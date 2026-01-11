import type { Metadata } from "next";
import { Geist, Geist_Mono, Merriweather } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const merriweather = Merriweather({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["300", "400", "700", "900"],
});

export const metadata: Metadata = {
  title: "AutoApply",
  description: "Automated Job Application Assistant",
};

import { Sidebar } from "@/components/layout/sidebar";
import { Toaster } from "sonner";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${merriweather.variable} antialiased flex h-screen overflow-hidden bg-background text-foreground`}
      >
        <Sidebar className="flex-none w-[280px] border-r" />
        <main className="flex-1 overflow-y-auto bg-background relative">
          <div className="container-tight px-6 py-8 md:px-8 md:py-12">
            {children}
          </div>
        </main>
        <Toaster />
      </body>
    </html>
  );
}
