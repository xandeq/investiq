# Fix Style Violations

Analyze and fix the following style issues in the code:
$ARGUMENTS

## Style Guide Violations to Fix

### 1. Global Element Styles
- Remove any global element selectors (button {}, a {}, etc.)
- Replace with Tailwind utilities or shadcn/ui components

### 2. Hardcoded Colors
- Replace hardcoded colors with theme variables:
  - `text-black` → `text-foreground`
  - `bg-white` → `bg-background`
  - `text-gray-500` → `text-muted-foreground`
  - `border-gray-200` → `border-border`
  - `bg-blue-500` → `bg-primary`
  - `text-red-500` → `text-destructive`

### 3. Raw HTML Elements
- Replace `<button>` with `<Button>` component
- Replace `<input>` with `<Input>` component
- Replace raw cards with `<Card>` component
- Add proper imports from `@/components/ui/*`

### 4. Inline Styles
- Convert inline styles to Tailwind utilities:
  - `style="padding: 16px"` → `className="p-4"`
  - `style="margin: 8px 0"` → `className="my-2"`
  - `style="display: flex"` → `className="flex"`

### 5. Dark Mode Compatibility
- Ensure all colors use theme variables
- Add dark mode variants where needed
- Test that contrast is maintained

### 6. Component Structure
- Use proper shadcn/ui component composition:
  ```tsx
  <Card>
    <CardHeader>
      <CardTitle>Title</CardTitle>
      <CardDescription>Description</CardDescription>
    </CardHeader>
    <CardContent>Content</CardContent>
  </Card>
  ```

### 7. Accessibility
- Add alt text to images
- Ensure form inputs have associated labels
- Add proper ARIA attributes where needed

## Provide:
1. Fixed code with all violations resolved
2. List of changes made
3. Any additional improvements for better maintainability