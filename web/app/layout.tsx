import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Admind Deck Builder",
  description: "On-premise AI presentation builder",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
