import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';

export function Tabs({ value, onValueChange, children, className = '' }: {
  value: string;
  onValueChange: (v: string) => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onValueChange} className={className}>
      {children}
    </TabsPrimitive.Root>
  );
}

export function TabsList({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <TabsPrimitive.List className={className}>
      {children}
    </TabsPrimitive.List>
  );
}

export function TabsTrigger({ value, children, title }: { value: string; children: React.ReactNode; title?: string }) {
  return (
    <TabsPrimitive.Trigger
      value={value}
      title={title}
      className="flex items-center justify-center p-2 rounded-md text-jarvis-textMuted data-[state=active]:bg-jarvis-card data-[state=active]:text-jarvis-primary transition-colors"
    >
      {children}
    </TabsPrimitive.Trigger>
  );
}

export function TabsContent({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <TabsPrimitive.Content value={value}>
      {children}
    </TabsPrimitive.Content>
  );
}
