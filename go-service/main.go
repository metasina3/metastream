package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
)

var rdb *redis.Client
var ctx = context.Background()

func init() {
	// Initialize Redis client
	rdb = redis.NewClient(&redis.Options{
		Addr:     "redis:6379",
		Password: "",
		DB:       0,
	})

	// Test connection
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatal("Failed to connect to Redis:", err)
	}
}

type CheckUpdateRequest struct {
	StreamID int64 `json:"stream_id" binding:"required"`
	LastID   int64 `json:"last_id"`
}

type Comment struct {
	ID        int64  `json:"id"`
	Username  string `json:"username"`
	Message   string `json:"message"`
	Timestamp int64  `json:"timestamp"`
}

type UpdateCheckResponse struct {
	HasUpdates    bool      `json:"has_updates"`
	Comments      []Comment `json:"comments,omitempty"`
	Online        int       `json:"online,omitempty"`
	AllowComments bool      `json:"allow_comments"`
}

type HeartbeatRequest struct {
	StreamID int64  `json:"stream_id" binding:"required"`
	ViewerID string `json:"viewer_id"`
}

func checkUpdate(c *gin.Context) {
	var req CheckUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	// Get comments that should be published now (timestamp <= now) and are newer than last_id
	now := time.Now().Unix() * 1000

	// Redis keys
	sid := fmt.Sprintf("%d", req.StreamID)
	idxKey := fmt.Sprintf("comments:index:%s", sid)
	dataKey := fmt.Sprintf("comments:data:%s", sid)
	onlineKey := fmt.Sprintf("online:%d", req.StreamID)

	// Get comment IDs ready to publish (timestamp <= now)
	reqCtx := c.Request.Context()
	var ids []string
	var err error
	
	if req.LastID == 0 {
		// Initial load: get all comments (last 100 to avoid loading too many)
		zMembers, zErr := rdb.ZRangeByScoreWithScores(reqCtx, idxKey, &redis.ZRangeBy{
			Min: "0",                    // From beginning
			Max: strconv.FormatInt(now, 10), // Only those ready (timestamp <= now)
		}).Result()
		
		// Get only the IDs (not scores) and take last 100
		idStrings := make([]string, 0)
		if zErr == nil {
			for _, z := range zMembers {
				if memberStr, ok := z.Member.(string); ok {
					idStrings = append(idStrings, memberStr)
				}
			}
			// Take last 100 comments
			if len(idStrings) > 100 {
				idStrings = idStrings[len(idStrings)-100:]
			}
		} else {
			log.Printf("[GO] Error getting initial comments from Redis: %v", zErr)
		}
		ids = idStrings
		err = zErr // Set err for later use
	} else {
		// Update: get only new ones after last_id
		ids, err = rdb.ZRangeByScore(reqCtx, idxKey, &redis.ZRangeBy{
			Min: strconv.FormatInt(req.LastID+1, 10), // Only new ones after last_id
			Max: strconv.FormatInt(now, 10),           // Only those ready (timestamp <= now)
		}).Result()
		if err != nil {
			log.Printf("[GO] Error getting updated comments from Redis: %v", err)
			ids = []string{} // Set empty slice on error
		}
	}

	// Get allow_comments status from Redis FIRST (set by backend when toggled)
	allowCommentsKey := fmt.Sprintf("stream:allow_comments:%d", req.StreamID)
	allowCommentsStr, err := rdb.Get(reqCtx, allowCommentsKey).Result()
	allowComments := true // Default to true if not set
	if err == nil {
		// Check for "1" (true) or "true" (string), anything else is false
		allowComments = allowCommentsStr == "1" || allowCommentsStr == "true"
		log.Printf("[GO] Stream %d: allow_comments from Redis = '%s' -> %v", req.StreamID, allowCommentsStr, allowComments)
	} else {
		log.Printf("[GO] Stream %d: allow_comments not found in Redis, defaulting to true (error: %v)", req.StreamID, err)
	}

	comments := []Comment{}

	// Only get comments if allow_comments is true
	if allowComments {
		if len(ids) > 0 {
			// Get full comment data
			data, dataErr := rdb.HMGet(reqCtx, dataKey, ids...).Result()
			if dataErr == nil {
				for _, d := range data {
					if d == nil {
						continue
					}
					
					var cmt Comment
					if jsonErr := json.Unmarshal([]byte(d.(string)), &cmt); jsonErr == nil {
						comments = append(comments, cmt)
					}
				}
			} else {
				log.Printf("[GO] Error getting comment data from Redis: %v", dataErr)
			}
		} else {
			log.Printf("[GO] Stream %d: No comment IDs found (err: %v, ids count: %d)", req.StreamID, err, len(ids))
		}
	}

	// Get online count
	online, err := rdb.SCard(reqCtx, onlineKey).Result()
	if err != nil {
		online = 0
	}

	resp := UpdateCheckResponse{
		HasUpdates:    len(comments) > 0 && allowComments,
		Comments:      comments,
		Online:        int(online),
		AllowComments: allowComments,
	}

	log.Printf("[GO] Stream %d: Returning %d comments, has_updates=%v, allow_comments=%v", req.StreamID, len(comments), resp.HasUpdates, allowComments)
	c.JSON(200, resp)
}

func heartbeat(c *gin.Context) {
	var req HeartbeatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	// Add viewer to online set with 2 minute expiration
	onlineKey := fmt.Sprintf("online:%d", req.StreamID)
	reqCtx := c.Request.Context()
	
	// Add viewer with 2 minute TTL
	err := rdb.SAdd(reqCtx, onlineKey, req.ViewerID).Err()
	if err == nil {
		// Set expiration to 2 minutes (120 seconds)
		rdb.Expire(reqCtx, onlineKey, 120*time.Second)
	}

	c.JSON(200, gin.H{"success": true})
}

func health(c *gin.Context) {
	c.JSON(200, gin.H{"status": "healthy", "service": "comment-polling"})
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

func main() {
	r := gin.Default()
	r.Use(corsMiddleware())

	// Routes
	r.POST("/check-update", checkUpdate)
	r.POST("/heartbeat", heartbeat)
	r.GET("/health", health)

	// Start server
	port := ":9000"
	log.Printf("Starting Go service on %s", port)
	if err := http.ListenAndServe(port, r); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}

