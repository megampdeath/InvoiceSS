import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Invoice SaaS",
  description: "Invoice extraction and review workflow"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
