"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, ClipboardList, ImageUp, Loader2, ShieldCheck, Zap } from "lucide-react";
import { API_BASE, saveConversion } from "../lib/flow";
import ConversionProgressModal from "../components/ConversionProgressModal";

export default function CapturePage() {
  const router = useRouter();
  const [ledgerText, setLedgerText] = useState("");
  const [chatText, setChatText] = useState("");
  const [productHints, setProductHints] = useState("");
  const [ledgerFiles, setLedgerFiles] = useState([]);
  const [productFiles, setProductFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [jobId, setJobId] = useState("");
  const [error, setError] = useState("");
  const ledgerInputRef = useRef(null);
  const productInputRef = useRef(null);

  async function runConversion(event) {
    event?.preventDefault();
    if (!ledgerText.trim() && !chatText.trim() && ledgerFiles.length === 0) {
      setError("Add ledger text, a handwritten ledger image, or order text before converting.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = new FormData();
      ledgerFiles.forEach((file) => payload.append("ledger_images", file));
      productFiles.forEach((file) => payload.append("product_images", file));
      payload.append("ledger_text", ledgerText);
      payload.append("chat_text", chatText);
      payload.append("product_hints", productHints);

      const response = await fetch(`${API_BASE}/api/conversions`, { method: "POST", body: payload });
      if (!response.ok) throw new Error(await apiError(response));
      const job = await response.json();
      setJobId(job.job_id);
      setShowProgress(true);
    } catch (conversionError) {
      setError(conversionError.message || "Conversion failed.");
      setShowProgress(false);
      setBusy(false);
    }
  }

  function handleProgressComplete(result) {
    saveConversion(result);
    setBusy(false);
    setShowProgress(false);
    router.push("/step-2");
  }

  return (
    <main className="flow-page">
      <ConversionProgressModal
        active={showProgress}
        jobId={jobId}
        onComplete={handleProgressComplete}
        onDismiss={() => {
          setShowProgress(false);
          setBusy(false);
        }}
        error={error}
      />

      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Step 1</p>
          <h1>Turn your source records into a working ERP.</h1>
          <p>Everything on this screen is submitted by you. The pipeline records its source, status, and measured runtime for every stage.</p>
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
            <Field
              label="Product labels (one per uploaded photo)"
              value={productHints}
              onChange={setProductHints}
              placeholder={"Sugar\nBasmati rice\nParle-G"}
              compact
            />
            <Field
              label="Ledger transcription"
              value={ledgerText}
              onChange={setLedgerText}
              placeholder="2026-09-10 ramesh: chini 2 kg Rs 88"
            />
            <Field
              label="Chat orders"
              value={chatText}
              onChange={setChatText}
              placeholder="kavya: 2 kg atta, Rs 76"
            />
            <div className="button-row">
              <button className="primary-button" type="submit" disabled={busy}>
                {busy ? <Loader2 className="spin" size={17} /> : <Zap size={17} />}
                Run conversion
              </button>
            </div>
            <p className="hint-line"><ShieldCheck size={14} /> No sample rows are injected. Missing prices remain unpriced instead of being estimated.</p>
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

function Field({ label, value, onChange, placeholder, compact = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea className={compact ? "compact" : ""} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

async function apiError(response) {
  try {
    const payload = await response.json();
    return payload.detail || "Conversion could not be started.";
  } catch {
    return "Conversion could not be started.";
  }
}
