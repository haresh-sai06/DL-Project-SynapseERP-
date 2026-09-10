import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flow-page">
      <section className="empty-step">
        <h1>404 - Page Not Found</h1>
        <p>The page or surface you are looking for does not exist in Synapse ERP.</p>
        <Link href="/" className="primary-button">
          Return to Home
        </Link>
      </section>
    </main>
  );
}
