---
description: Create a properly structured shadcn/ui component with theme support
allowed-tools: Write, Read
argument-hint: Describe the component you want to create
---

# Create shadcn/ui Component

Create a shadcn/ui component based on the following requirements:
$ARGUMENTS

## Component Structure Template

```tsx
import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface ComponentProps {
  className?: string
  children?: React.ReactNode
  // Add other props
}

export function ComponentName({ 
  className,
  children,
  ...props 
}: ComponentProps) {
  return (
    <div className={cn(
      // Base styles using theme variables
      "bg-background text-foreground",
      // Responsive styles
      "p-4 md:p-6 lg:p-8",
      // Allow className override
      className
    )} {...props}>
      {children}
    </div>
  )
}
```

## Requirements

### 1. Theme Variables
- Use only theme color variables (foreground, background, primary, etc.)
- Never hardcode colors

### 2. Component Composition
- Use existing shadcn/ui components
- Follow shadcn/ui patterns for consistency

### 3. Styling Approach
- Use Tailwind utilities
- Apply cn() utility for className merging
- Support className prop for customization

### 4. Dark Mode
- Ensure component works in both light and dark modes
- Use theme variables that auto-adjust

### 5. Accessibility
- Include proper ARIA attributes
- Support keyboard navigation
- Ensure proper contrast ratios

### 6. Responsive Design
- Mobile-first approach
- Use responsive Tailwind prefixes (sm:, md:, lg:)

## Deliver:
1. Complete component code
2. Usage examples
3. Props documentation
4. Any required imports