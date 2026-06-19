import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { Plus, Trash2, Play } from "lucide-react";

export default function Keywords() {
  const [keywords, setKeywords] = useState([]);
  const [value, setValue] = useState("");
  const [type, setType] = useState("name");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const r = await api.get("/keywords");
    setKeywords(r.data.keywords);
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.post("/keywords", { value, type });
      setValue("");
      load();
    } catch (e) { setErr(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const del = async (id) => {
    await api.delete(`/keywords/${id}`);
    load();
  };

  const scan = async (id) => {
    await api.post("/scan/run", { keyword_id: id });
    alert("Scan queued. You'll receive an email if new findings are detected.");
  };

  return (
    <DashboardLayout title="Monitored Keywords">
      <div className="brutal-card p-6 mb-6">
        <div className="overline mb-3">// add keyword</div>
        <form onSubmit={add} className="flex flex-col md:flex-row gap-3" data-testid="add-keyword-form">
          <input data-testid="keyword-value" value={value} onChange={(e)=>setValue(e.target.value)} placeholder="e.g. John Doe / john@example.com / 555-1234" className="brutal-input flex-1" required />
          <select data-testid="keyword-type" value={type} onChange={(e)=>setType(e.target.value)} className="brutal-input md:w-48">
            {["name","email","phone","address","other"].map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button data-testid="add-keyword-btn" type="submit" disabled={busy} className="brutal-btn brutal-btn-primary flex items-center gap-2"><Plus size={14}/>Add</button>
        </form>
        {err && <div className="mt-2 font-mono text-xs text-[#FF3333]" data-testid="keyword-error">› {err}</div>}
      </div>

      <div className="brutal-card p-6">
        <div className="overline mb-3">// monitored ({keywords.length})</div>
        {keywords.length === 0 ? (
          <div className="font-mono text-zinc-500 py-6">No keywords yet. Add your name, email, or phone above to start monitoring.</div>
        ) : (
          <table className="w-full" data-testid="keywords-table">
            <thead><tr className="border-b border-[#222]">
              {["Value","Type","Last Scan","Action"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
            </tr></thead>
            <tbody>
              {keywords.map(k => (
                <tr key={k.id} className="border-b border-[#222] hover:bg-[#0a0a0a]" data-testid={`keyword-row-${k.id}`}>
                  <td className="py-3 font-mono text-sm">{k.value}</td>
                  <td className="py-3 font-mono text-xs text-zinc-400 uppercase">{k.type}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{k.last_scan_at?.slice(0,16) || "never"}</td>
                  <td className="py-3 flex gap-3">
                    <button onClick={()=>scan(k.id)} data-testid={`scan-keyword-${k.id}`} className="font-mono text-xs text-[#00FF41] hover:text-white flex items-center gap-1"><Play size={12}/>SCAN</button>
                    <button onClick={()=>del(k.id)} data-testid={`delete-keyword-${k.id}`} className="font-mono text-xs text-[#FF3333] hover:text-white flex items-center gap-1"><Trash2 size={12}/>DELETE</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  );
}
