import Link from "next/link";
import { ArrowRight, BadgeCheck, BrainCircuit, Cpu, FileJson, FileText, Radio, ShieldCheck, Sparkles, Tags } from "lucide-react";
import LiveTicker from "./components/LiveTicker";
import { API_BASE } from "./lib/flow";

const PRETRAINED_FEATURES = [
  {
    icon: FileText,
    title: "TrOCR Handwritten OCR",
    desc: "Microsoft's pre-trained Transformer OCR (microsoft/trocr-base-handwritten) reads khata ledger lines without any fine-tuning.",
    label: "Pre-trained on IAM handwriting",
  },
  {
    icon: Tags,
    title: "BERT Multilingual NER",
    desc: "dslim/bert-base-NER extracts product names, quantities, prices, and customer names from Hinglish WhatsApp orders.",
    label: "Fine-tuned NER model",
  },
  {
    icon: Cpu,
    title: "Real-time trained CNNs",
    desc: "Custom CNN trained on real MNIST (98.3% accuracy) and LSTM trained on live USD/INR FX series for demand forecasting.",
    label: "Trained on real data",
  },
];

export default function LandingPage() {
  return (
    <main className="landing-page">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow"><Sparkles size={16} /> Multimodal DL + OCR platform</p>
          <h1>Convert an offline shop into a live SaaS workspace.</h1>
          <p>
            Synapse ERP turns handwritten khata photos, product images, and WhatsApp orders into inventory,
            CRM, invoices, analytics, exports, and an authenticated CRUD workspace — powered by real
            pre-trained deep learning models.
          </p>
          <div className="hero-actions">
            <Link className="primary-button hero-button" href="/step-1">
              Start conversion
              <ArrowRight size={18} />
            </Link>
            <Link className="secondary-button hero-button" href="/live">
              <Radio size={16} /> Live data &amp; training
            </Link>
          </div>
          <div className="landing-proof">
            <span><BrainCircuit size={16} /> TrOCR · BERT · CNN</span>
            <span><ShieldCheck size={16} /> Authenticated ERP workspace</span>
            <span><FileJson size={16} /> JSON, CSV, HTML outputs</span>
          </div>
        </div>

        <div className="landing-visual">
          <div className="visual-browser">
            <div className="browser-bar">
              <span />
              <span />
              <span />
              <p>synapse.erp/generated-workspace</p>
            </div>
            <img src={`${API_BASE}/project-assets/architecture.png`} alt="Synapse ERP conversion architecture" />
          </div>
          <div className="visual-card top-card">
            <BadgeCheck size={18} />
            <strong>9 backend nodes online</strong>
          </div>
          <div className="visual-card bottom-card">
            <strong>Final output</strong>
            <span>ERP + CRUD + exports</span>
          </div>
          <LiveTicker />
        </div>
      </section>

      <section className="pretrained-showcase">
        <div className="showcase-head">
          <p className="eyebrow"><Cpu size={15} /> Pre-trained &amp; real-trained models</p>
          <h2>Production-grade deep learning out of the box</h2>
          <p>No mocked pipelines. Every model either loads pre-trained weights or trains on real data.</p>
        </div>
        <div className="showcase-grid">
          {PRETRAINED_FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div className="showcase-card" key={f.title}>
                <div className="showcase-icon"><Icon size={20} /></div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
                <span className="showcase-tag">{f.label}</span>
              </div>
            );
          })}
        </div>
        <div className="showcase-cta">
          <Link href="/models" className="primary-button hero-button">
            <Cpu size={16} /> Explore Model Hub
            <ArrowRight size={18} />
          </Link>
          <Link href="/live" className="secondary-button hero-button">
            Live data dashboard →
          </Link>
        </div>
      </section>
    </main>
  );
}
