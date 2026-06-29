import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Virtuals Surge Sniper",
  description: "Virtuals Protocol intelligence dashboard + automated investment arm",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
