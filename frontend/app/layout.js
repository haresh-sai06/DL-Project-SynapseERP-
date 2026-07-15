import "./globals.css";
import SidebarLayout from "./components/SidebarLayout";

export const metadata = {
  title: "Synapse ERP | Offline to SaaS Converter",
  description: "Multimodal OCR and deep learning platform for converting offline MSME records into a live ERP with real-time data and trained models."
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Sora:wght@600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <SidebarLayout>{children}</SidebarLayout>
      </body>
    </html>
  );
}
