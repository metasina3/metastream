/**
 * MetaStream Color System Usage Examples
 * 
 * This file demonstrates how to use the new color system
 * with Tailwind classes and CSS variables.
 */

import React from 'react'

export default function ColorSystemExample() {
  return (
    <div className="min-h-screen bg-bg p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header with Gradient Text */}
        <header className="text-center py-8">
          <h1 className="text-5xl font-bold text-gradient mb-4">
            MetaStream
          </h1>
          <p className="text-text-secondary text-lg">
            Futuristic Streaming Platform
          </p>
        </header>

        {/* Buttons Section */}
        <section className="card space-y-4">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Buttons</h2>
          
          <div className="flex flex-wrap gap-4">
            {/* Primary Gradient Button */}
            <button className="btn-primary">
              Primary Button
            </button>
            
            {/* Secondary Button */}
            <button className="btn-secondary">
              Secondary Button
            </button>
            
            {/* Accent Button */}
            <button className="btn-accent">
              Accent Button
            </button>
            
            {/* Custom Gradient Button with Tailwind */}
            <button className="px-6 py-3 rounded-lg font-medium text-white bg-gradient-primary hover:shadow-glow transition-all">
              Custom Gradient
            </button>
          </div>
        </section>

        {/* Cards Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Cards</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Standard Card */}
            <div className="card">
              <h3 className="text-xl font-bold text-text-primary mb-2">
                Standard Card
              </h3>
              <p className="text-text-secondary">
                This card uses the standard card class with surface background.
              </p>
            </div>
            
            {/* Card with Gradient Border */}
            <div className="surface-gradient">
              <h3 className="text-xl font-bold text-text-primary mb-2">
                Gradient Border
              </h3>
              <p className="text-text-secondary">
                This card has a subtle gradient border effect.
              </p>
            </div>
            
            {/* Card with Glow */}
            <div className="card glow">
              <h3 className="text-xl font-bold text-text-primary mb-2">
                Glow Effect
              </h3>
              <p className="text-text-secondary">
                This card has a neon glow effect.
              </p>
            </div>
          </div>
        </section>

        {/* Form Elements Section */}
        <section className="card space-y-4">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Form Elements</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-text-primary mb-2 font-medium">
                Input Field
              </label>
              <input 
                type="text" 
                placeholder="Enter text..." 
                className="input w-full"
              />
            </div>
            
            <div>
              <label className="block text-text-primary mb-2 font-medium">
                Textarea
              </label>
              <textarea 
                placeholder="Enter description..." 
                className="input w-full min-h-[100px]"
              />
            </div>
          </div>
        </section>

        {/* Color Palette Display */}
        <section className="card">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Color Palette</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Primary Colors */}
            <div className="space-y-2">
              <div className="h-20 rounded-lg bg-gradient-primary"></div>
              <p className="text-sm text-text-secondary">Primary Gradient</p>
            </div>
            
            <div className="space-y-2">
              <div className="h-20 rounded-lg bg-primary"></div>
              <p className="text-sm text-text-secondary">Primary (#00C6FF)</p>
            </div>
            
            <div className="space-y-2">
              <div className="h-20 rounded-lg bg-secondary"></div>
              <p className="text-sm text-text-secondary">Secondary (#7B2FF7)</p>
            </div>
            
            <div className="space-y-2">
              <div className="h-20 rounded-lg bg-accent"></div>
              <p className="text-sm text-text-secondary">Accent (#3AE7FF)</p>
            </div>
          </div>
        </section>

        {/* Text Colors */}
        <section className="card">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Text Colors</h2>
          
          <div className="space-y-2">
            <p className="text-text-primary text-lg">
              Primary Text - Main content text color
            </p>
            <p className="text-text-secondary text-lg">
              Secondary Text - Supporting text color
            </p>
            <p className="text-accent text-lg">
              Accent Text - Highlighted text color
            </p>
            <p className="text-gradient text-lg font-bold">
              Gradient Text - Gradient text effect
            </p>
          </div>
        </section>

        {/* Background Colors */}
        <section className="card">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Background Colors</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-bg border border-border">
              <p className="text-text-primary font-medium">Background</p>
              <p className="text-text-secondary text-sm">Main page background</p>
            </div>
            
            <div className="p-4 rounded-lg bg-bg-surface border border-border">
              <p className="text-text-primary font-medium">Surface</p>
              <p className="text-text-secondary text-sm">Card/container background</p>
            </div>
          </div>
        </section>

        {/* Glow Effects */}
        <section className="card">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Glow Effects</h2>
          
          <div className="flex flex-wrap gap-4">
            <div className="px-6 py-4 rounded-lg bg-bg-surface glow">
              Standard Glow
            </div>
            
            <div className="px-6 py-4 rounded-lg bg-bg-surface glow-lg">
              Large Glow
            </div>
            
            <div className="px-6 py-4 rounded-lg bg-bg-surface shadow-glow-purple">
              Purple Glow
            </div>
            
            <div className="px-6 py-4 rounded-lg bg-bg-surface animate-glow-pulse">
              Pulsing Glow
            </div>
          </div>
        </section>

        {/* Usage with Tailwind Classes */}
        <section className="card">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Tailwind Class Usage</h2>
          
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-bg-surface border border-border">
              <code className="text-sm text-text-secondary">
                className="bg-bg-surface text-text-primary border border-border"
              </code>
            </div>
            
            <div className="p-4 rounded-lg bg-gradient-primary text-white">
              <code className="text-sm">
                className="bg-gradient-primary text-white"
              </code>
            </div>
            
            <div className="p-4 rounded-lg bg-bg-surface border border-accent">
              <code className="text-sm text-accent">
                className="border border-accent text-accent"
              </code>
            </div>
          </div>
        </section>

      </div>
    </div>
  )
}

