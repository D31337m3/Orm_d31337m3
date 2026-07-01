import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import PageBrandBanner from "@/components/PageBrandBanner";
import api from "@/lib/api";
import { motion } from "framer-motion";
import { FileText, Download, Trash2, FileSignature, Eye } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";

const TEMPLATE_ICONS = {
  dmca_takedown: "⚖",
  cease_and_desist: "⛔",
  privacy_removal_request: "🔒",
  right_to_be_forgotten: "🌐",
};

const PREPOPULATED_TEMPLATES = [
  {
    id: "dmca_takedown",
    title: "DMCA Takedown Notice",
    summary: "Formal copyright takedown demand under the U.S. Digital Millennium Copyright Act.",
    jurisdictions: ["US"],
    available: true,
  },
  {
    id: "cease_and_desist",
    title: "Cease & Desist Letter",
    summary: "Formal demand to stop publication, distribution, or sale of personal data.",
    jurisdictions: ["US", "CA", "MX"],
    available: true,
  },
  {
    id: "privacy_removal_request",
    title: "Privacy Removal Request",
    summary: "Jurisdiction-aware data deletion request under applicable privacy laws.",
    jurisdictions: ["US", "CA", "MX"],
    available: true,
  },
  {
    id: "right_to_be_forgotten",
    title: "Right to be Forgotten - Search Engine De-indexing",
    summary: "Request to search engines to de-index URLs surfacing personal data.",
    jurisdictions: ["US", "CA", "MX"],
    available: true,
  },
];

function mergeTemplates(apiTemplates) {
  const incoming = Array.isArray(apiTemplates) ? apiTemplates : [];
  const byId = new Map(incoming.filter((t) => t?.id).map((t) => [t.id, t]));

  const merged = PREPOPULATED_TEMPLATES.map((seed) => {
    const api = byId.get(seed.id) || {};
    return {
      ...seed,
      ...api,
      jurisdictions: Array.isArray(api.jurisdictions) && api.jurisdictions.length ? api.jurisdictions : seed.jurisdictions,
      available: typeof api.available === "boolean" ? api.available : seed.available,
    };
  });

  for (const t of incoming) {
    if (t?.id && !merged.some((m) => m.id === t.id)) merged.push(t);
  }

  return merged;
}

export default function Documents() {
  const { user: me } = useAuth();
  const [tab, setTab] = useState("documents");
  const [templates, setTemplates] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [findings, setFindings] = useState([]);
  const [signature, setSignature] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [genForm, setGenForm] = useState({ template_id: "", finding_id: "", recipient_broker: "", recipient_address: "" });

  const buildWitnessSignaturePayloadIfNeeded = () => {
    if (!me?.is_admin || !signature?.data_url) return {};
    return {
      witness_signed_name: signature.full_name || me?.name || me?.email || "Admin Witness",
      witness_signature_image: signature.data_url,
      witness_signed_at: new Date().toISOString(),
      witness_role: "admin_witness",
      auto_filled_witness: true,
    };
  };

  const load = async () => {
    const [t, d, f, s] = await Promise.allSettled([
      api.get("/documents/templates"),
      api.get("/documents"),
      api.get("/findings"),
      api.get("/signature"),
    ]);

    const apiTemplates = t.status === "fulfilled" ? t.value?.data?.templates : [];
    setTemplates(mergeTemplates(apiTemplates));
    setDocuments(d.status === "fulfilled" ? (d.value?.data?.documents || []) : []);
    setFindings(f.status === "fulfilled" ? (f.value?.data?.findings || []) : []);
    setSignature(s.status === "fulfilled" ? (s.value?.data?.signature || null) : null);
  };
  useEffect(() => { load(); }, []);

  // If user clicked "Legal" on a finding, jump straight to Generate tab pre-filled
  useEffect(() => {
    const pending = sessionStorage.getItem("d31337m3_pending_finding");
    if (pending) {
      try {
        const { finding_id, broker } = JSON.parse(pending);
        setGenForm((g) => ({ ...g, finding_id, recipient_broker: broker || "" }));
        setTab("generate");
      } catch (e) { /* ignore */ }
      sessionStorage.removeItem("d31337m3_pending_finding");
    }
  }, []);

  const generate = async () => {
    if (!genForm.template_id) return;
    setGenerating(true);
    try {
      const r = await api.post("/documents/generate", genForm);
      setViewing(r.data.document);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to generate");
    } finally { setGenerating(false); }
  };

  const sign = async (id) => {
    try {
      const r = await api.post("/documents/sign", {
        document_id: id,
        ...buildWitnessSignaturePayloadIfNeeded(),
      });
      const fresh = await api.get(`/documents/${id}`);
      setViewing(fresh.data.document);
      load();
      const d = r.data.dispatch || {};
      if (d.delivered && d.broker_email) {
        alert(`✓ Signed & dispatched to ${d.broker_email}`);
      } else if (d.form_url) {
        alert(`✓ Signed. This broker requires manual submission via their opt-out form:\n${d.form_url}`);
      } else {
        alert("✓ Document signed.");
      }
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete document?")) return;
    await api.delete(`/documents/${id}`);
    load();
  };

  const downloadTxt = (doc) => {
    const blob = new Blob([doc.body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${doc.title.replace(/[^a-z0-9]/gi, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const printDoc = (doc) => {
    const w = window.open("", "_blank");
    if (!w) return;
    const sigHtml = doc.signature_image
      ? `<div style="margin-top:30px"><img src="${doc.signature_image}" style="max-height:80px;background:#fff;padding:6px;border:1px solid #ccc"/><div style="font-family:monospace;font-size:12px;color:#666;margin-top:6px">Electronically signed by ${doc.signed_name} on ${doc.signed_at}</div></div>`
      : "";
    w.document.write(`<html><head><title>${doc.title}</title><style>body{font-family:Georgia,serif;max-width:780px;margin:40px auto;padding:0 20px;line-height:1.6;color:#111}pre{white-space:pre-wrap;font-family:Georgia,serif;font-size:14px}</style></head><body><h1>${doc.title}</h1><pre>${doc.body}</pre>${sigHtml}</body></html>`);
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 300);
  };

  return (
    <DashboardLayout title="Legal Documents — North America">
      <PageBrandBanner title="documents" description="Purple-branded legal workflow for notices, signatures, and exports." />
      <div className="brutal-card p-4 mb-6 border-[#A855F7]/40 bg-[#120f1f]/30">
        <div className="font-mono text-xs text-zinc-300">
          <span className="text-[#A855F7] font-bold">// JURISDICTION:</span> Legal document services are available exclusively for residents of
          <span className="text-white"> Canada (PIPEDA/Quebec Law 25)</span>,
          <span className="text-white"> United States (CCPA/CPRA/DMCA)</span>, and
          <span className="text-white"> México (LFPDPPP)</span>.
          Documents are e-signed under ESIGN Act / UECA / LFFEA.
        </div>
      </div>

      <div className="flex gap-2 mb-6" data-testid="docs-tabs">
        {[["documents","My Documents"],["generate","Generate New"]].map(([k,l]) => (
          <button key={k} onClick={()=>setTab(k)} data-testid={`docs-tab-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${tab===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "documents" && (
        <div className="brutal-card p-6" data-testid="documents-panel">
          {documents.length === 0 ? (
            <div className="font-mono text-zinc-500 py-6">No documents yet. Go to <button onClick={()=>setTab("generate")} className="text-[#A855F7]">Generate New →</button> to create your first legal notice.</div>
          ) : (
            <table className="w-full">
              <thead><tr className="border-b border-[#222]">
                {["Title","Recipient","Country","Status","Created","Actions"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
              </tr></thead>
              <tbody>
                {documents.map(d => (
                  <tr key={d.id} className="border-b border-[#222] hover:bg-[#0a0a0a]" data-testid={`document-row-${d.id}`}>
                    <td className="py-3 font-mono text-sm">{TEMPLATE_ICONS[d.template_id]} {d.title}</td>
                    <td className="py-3 font-mono text-xs text-zinc-400">{d.recipient_broker}</td>
                    <td className="py-3 font-mono text-xs">{d.country}</td>
                    <td className="py-3 font-mono text-xs">
                      {d.status === "signed"
                        ? <span className="text-[#00FF41]">SIGNED</span>
                        : <span className="text-[#FFD700]">DRAFT</span>}
                    </td>
                    <td className="py-3 font-mono text-xs text-zinc-500">{d.created_at?.slice(0,10)}</td>
                    <td className="py-3 flex gap-3">
                      <button onClick={()=>setViewing(d)} data-testid={`view-doc-${d.id}`} className="text-zinc-400 hover:text-white" title="View"><Eye size={14}/></button>
                      {d.status !== "signed" && (
                        <button onClick={()=>sign(d.id)} data-testid={`sign-doc-${d.id}`} className="text-[#00FF41] hover:text-white" title="Sign"><FileSignature size={14}/></button>
                      )}
                      <button onClick={()=>downloadTxt(d)} data-testid={`download-doc-${d.id}`} className="text-zinc-400 hover:text-white" title="Download"><Download size={14}/></button>
                      <button onClick={()=>del(d.id)} data-testid={`delete-doc-${d.id}`} className="text-[#FF3333] hover:text-white" title="Delete"><Trash2 size={14}/></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "generate" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="generate-panel">
          <div className="brutal-card p-6">
            <div className="overline mb-3">// pick a template</div>
            <div className="space-y-3">
              {templates.map(t => (
                <motion.button
                  whileHover={{ x: 4 }}
                  key={t.id}
                  onClick={() => t.available && setGenForm({...genForm, template_id: t.id})}
                  disabled={!t.available}
                  data-testid={`template-${t.id}`}
                  className={`w-full text-left border p-4 transition-all ${genForm.template_id===t.id ? "border-[#A855F7] bg-[#120f1f]" : t.available ? "border-[#222] hover:border-white" : "border-[#222] opacity-40 cursor-not-allowed"}`}
                >
                  <div className="font-display font-bold text-lg flex items-center gap-2">
                    <span className="text-2xl">{TEMPLATE_ICONS[t.id]}</span>{t.title}
                  </div>
                  <div className="font-mono text-xs text-zinc-400 mt-1">{t.summary}</div>
                  <div className="font-mono text-[10px] tracking-widest text-zinc-500 mt-2">
                    JURISDICTIONS: {t.jurisdictions.join(" · ")}
                    {!t.available && <span className="text-[#A855F7]"> · NOT AVAILABLE FOR YOUR COUNTRY</span>}
                  </div>
                </motion.button>
              ))}
            </div>
          </div>

          <div className="brutal-card p-6">
            <div className="overline mb-3">// document details</div>
            <div className="space-y-3">
              <div>
                <div className="overline mb-1">link to finding (optional)</div>
                <select data-testid="gen-finding" value={genForm.finding_id} onChange={(e)=>setGenForm({...genForm, finding_id: e.target.value})} className="brutal-input">
                  <option value="">— none —</option>
                  {findings.filter(f=>f.status==="active").map(f => (
                    <option key={f.id} value={f.id}>{f.broker} — {f.keyword_value}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="overline mb-1">recipient (broker / company name)</div>
                <input data-testid="gen-recipient" value={genForm.recipient_broker} onChange={(e)=>setGenForm({...genForm, recipient_broker: e.target.value})} placeholder="e.g. Spokeo Inc." className="brutal-input" />
              </div>
              <div>
                <div className="overline mb-1">recipient address</div>
                <input data-testid="gen-recipient-addr" value={genForm.recipient_address} onChange={(e)=>setGenForm({...genForm, recipient_address: e.target.value})} placeholder="123 Privacy Way, City, State, ZIP" className="brutal-input" />
              </div>
              <button onClick={generate} disabled={!genForm.template_id || generating} data-testid="generate-doc-btn" className="brutal-btn brutal-btn-primary w-full flex items-center gap-2 justify-center">
                <FileText size={14}/>{generating ? "Generating..." : "Generate Document"}
              </button>
              {!signature && (
                <div className="font-mono text-xs text-[#FFD700] mt-2">⚠ Heads up: you&apos;ll need an e-signature on file to sign generated documents. <Link to="/profile-signature" className="underline">Set one up →</Link></div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Viewer modal */}
      {viewing && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={()=>setViewing(null)} data-testid="doc-viewer">
          <div onClick={(e)=>e.stopPropagation()} className="brutal-card max-w-3xl w-full max-h-[90vh] overflow-y-auto p-8 bg-[#0a0a0a]">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="overline mb-1">// legal document</div>
                <h2 className="font-display font-black text-2xl">{viewing.title}</h2>
                <div className="font-mono text-xs text-zinc-500 mt-1">{viewing.country} · {viewing.status === "signed" ? <span className="text-[#00FF41]">SIGNED</span> : <span className="text-[#FFD700]">DRAFT</span>}</div>
              </div>
              <button onClick={()=>setViewing(null)} className="text-zinc-500 hover:text-white">✕</button>
            </div>
            <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap border border-[#222] p-5 bg-black mb-4">{viewing.body}</pre>
            {viewing.signature_image && (
              <div className="border border-[#222] p-3 bg-[#0a0a0a]">
                <div className="overline mb-2">// affixed signature</div>
                <img src={viewing.signature_image} alt="signature" className="max-h-20 bg-white p-2 inline-block" />
                <div className="font-mono text-xs text-zinc-500 mt-2">› {viewing.signed_name} · {viewing.signed_at?.slice(0,16)}</div>
              </div>
            )}
            {viewing.witness_signature_image && (
              <div className="border border-[#222] p-3 bg-[#0a0a0a] mt-3">
                <div className="overline mb-2">// witness signature</div>
                <img src={viewing.witness_signature_image} alt="witness signature" className="max-h-20 bg-white p-2 inline-block" />
                <div className="font-mono text-xs text-zinc-500 mt-2">› {viewing.witness_signed_name || "Witness"} · {viewing.witness_signed_at?.slice(0,16)}</div>
              </div>
            )}
            <div className="flex gap-3 mt-5">
              {viewing.status !== "signed" && <button onClick={()=>sign(viewing.id)} data-testid="viewer-sign-btn" className="brutal-btn brutal-btn-primary">Sign Now</button>}
              <button onClick={()=>printDoc(viewing)} data-testid="viewer-print-btn" className="brutal-btn">Print / Save PDF</button>
              <button onClick={()=>downloadTxt(viewing)} data-testid="viewer-download-btn" className="brutal-btn">Download .txt</button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
