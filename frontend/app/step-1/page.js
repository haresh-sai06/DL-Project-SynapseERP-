"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, ClipboardList, ImageUp, Loader2, Play, Zap } from "lucide-react";
import { API_BASE, saveConversion } from "../lib/flow";

const defaultLedger = `2026-06-01 ramesh: chini 2 kg Rs 88
2026-06-01 anita: rice 5 kg Rs 310
2026-06-02 salim: parle-g 10 pack Rs 100
2026-06-03 kavya: atta 3 kg Rs 114`;

const defaultChat = `kavya: bhaiya 2kg atta bhej do
mahesh: need 1 l oil today
anita: kal ke liye 3 kg dal`;

export default function CapturePage() {
  const router = useRouter();
  const [ledgerText, setLedgerText] = useState(defaultLedger);
  const [chatText, setChatText] = useState(defaultChat);
  const [productHints, setProductHints] = useState("sugar\nrice\nparle-g");
  const [ledgerFiles, setLedgerFiles] = useState([]);
  const [productFiles, setProductFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const ledgerInputRef = useRef(null);
  const productInputRef = useRef(null);

  async function runConversion(event) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = new FormData();
      ledgerFiles.forEach((file) => payload.append("ledger_images", file));
      productFiles.forEach((file) => payload.append("product_images", file));
      payload.append("ledger_text", ledgerText);
      payload.append("chat_text", chatText);
      payload.append("product_hints", productHints);
      const response = await fetch(`${API_BASE}/api/convert`, { method: "POST", body: payload });
      if (!response.ok) throw new Error(await response.text());
      saveConversion(await response.json());
      router.push("/step-2");
    } catch (conversionError) {
      setError(conversionError.message || "Conversion failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runDemo() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/demo-conversion`, { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      saveConversion(await response.json());
      router.push("/step-2");
    } catch (demoError) {
      setError(demoError.message || "Demo conversion failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flow-page">
      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Step 1</p>
          <h1>Capture the offline business records.</h1>
          <p>Upload handwritten note images, product photos, and paste the chat/order text that the shop already has.</p>
        </div>

        <form className="step-card capture-layout" onSubmit={runConversion}>
          <div className="capture-left">
            <div className="drop-grid">
              <FileDrop title="Handwritten notes" icon={ClipboardList} files={ledgerFiles} inputRef={ledgerInputRef} onChange={setLedgerFiles} />
              <FileDrop title="Product photos" icon={ImageUp} files={productFiles} inputRef={productInputRef} onChange={setProductFiles} />
            </div>
            <PreviewGrid files={[...ledgerFiles, ...productFiles]} />
          </div>

          <div className="capture-right">
            <Field label="Product names / SKU hints" value={productHints} onChange={setProductHints} compact />
            <Field label="OCR assist ledger text" value={ledgerText} onChange={setLedgerText} />
            <Field label="WhatsApp order text" value={chatText} onChange={setChatText} />
            <div className="button-row">
              <button className="primary-button" type="submit" disabled={busy}>
                {busy ? <Loader2 className="spin" size={17} /> : <Zap size={17} />}
                Run conversion
              </button>
              <button className="secondary-button" type="button" onClick={runDemo} disabled={busy}>
                <Play size={17} />
                Load demo
              </button>
            </div>
            <p className="hint-line">After conversion, you will move to Step 2: backend node execution.</p>
            {error && <p className="error">{error}</p>}
          </div>
        </form>

        <div className="next-strip">
          <span>Next page</span>
          <strong>Conversion nodes and extracted service status</strong>
          <ChevronRight size={20} />
        </div>
      </section>
    </main>
  );
}

function FileDrop({ title, icon: Icon, files, inputRef, onChange }) {
  return (
    <button className="file-drop large-drop" type="button" onClick={() => inputRef.current?.click()}>
      <input ref={inputRef} type="file" accept="image/*" multiple onChange={(event) => onChange(Array.from(event.target.files || []))} />
      <Icon size={24} />
      <strong>{title}</strong>
      <span>{files.length ? `${files.length} selected` : "Upload images"}</span>
    </button>
  );
}

function PreviewGrid({ files }) {
  if (!files.length) {
    return <div className="preview-empty">Image previews appear here after upload.</div>;
  }
  return (
    <div className="preview-strip">
      {files.slice(0, 6).map((file) => (
        <figure key={`${file.name}-${file.size}`}>
          <img src={URL.createObjectURL(file)} alt={file.name} />
          <figcaption>{file.name}</figcaption>
        </figure>
      ))}
    </div>
  );
}

function Field({ label, value, onChange, compact = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea className={compact ? "compact" : ""} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
