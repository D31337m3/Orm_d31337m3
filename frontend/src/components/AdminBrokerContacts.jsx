import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import AdminTable from "@/components/AdminTable";
import Drawer, { Field } from "@/components/Drawer";
import { Plus, Trash2, Save } from "lucide-react";

export default function AdminBrokerContacts() {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    const r = await api.get("/admin/broker-contacts");
    setRows(r.data.contacts || []);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!editing.broker) return alert("Broker name required");
    await api.post("/admin/broker-contacts", {
      broker: editing.broker, email: editing.email || null, form: editing.form || null,
    });
    setEditing(null);
    load();
  };

  const del = async (broker) => {
    if (!window.confirm(`Delete contact for ${broker}?`)) return;
    await api.delete(`/admin/broker-contacts/${encodeURIComponent(broker)}`);
    load();
  };

  const cols = [
    { key: "broker", label: "Broker", render: r => <span className="text-white font-bold">{r.broker}</span> },
    { key: "email", label: "Privacy Email", render: r => r.email || <span className="text-zinc-600">—</span> },
    { key: "form", label: "Opt-out Form", render: r => r.form ? <a href={r.form} target="_blank" rel="noopener noreferrer" onClick={(e)=>e.stopPropagation()} className="text-[#FF3333] hover:underline truncate inline-block max-w-[280px]">{r.form}</a> : <span className="text-zinc-600">—</span> },
    { key: "updated_at", label: "Updated", render: r => <span className="text-zinc-500">{r.updated_at?.slice(0,16)}</span> },
    { key: "actions", label: "", render: r => (
        <button onClick={(e)=>{ e.stopPropagation(); del(r.broker); }} data-testid={`bc-delete-${r.broker}`} className="text-[#FF3333] hover:text-white"><Trash2 size={14}/></button>
      ), csv: () => "" },
  ];

  return (
    <div data-testid="admin-broker-contacts">
      <div className="flex justify-between items-center mb-4">
        <p className="font-mono text-xs text-zinc-400">
          Edit broker privacy emails &amp; opt-out URLs. Used at scan time and document dispatch.
          Edits take effect within 5s — no redeploy required.
        </p>
        <button onClick={() => setEditing({ broker: "", email: "", form: "" })} data-testid="bc-new"
          className="brutal-btn brutal-btn-primary flex items-center gap-2 !py-2 !px-4 text-xs">
          <Plus size={14}/>New Broker
        </button>
      </div>

      <AdminTable
        testid="admin-broker-contacts-tbl" exportName="broker-contacts"
        data={rows} columns={cols} searchKeys={["broker","email","form"]}
        onRowClick={(r) => setEditing({ broker: r.broker, email: r.email || "", form: r.form || "" })}
      />

      <Drawer open={!!editing} onClose={() => setEditing(null)} title={editing?.broker ? `Edit · ${editing.broker}` : "New broker contact"} testid="bc-drawer">
        {editing && (
          <div className="space-y-4">
            <div>
              <div className="overline mb-1">broker name</div>
              <input data-testid="bc-name" value={editing.broker} onChange={(e) => setEditing({...editing, broker: e.target.value})} placeholder="e.g. Spokeo" className="brutal-input"/>
            </div>
            <div>
              <div className="overline mb-1">privacy email (we send signed legal docs here)</div>
              <input data-testid="bc-email" type="email" value={editing.email} onChange={(e) => setEditing({...editing, email: e.target.value})} placeholder="privacy@spokeo.com" className="brutal-input"/>
            </div>
            <div>
              <div className="overline mb-1">opt-out form url (fallback when no email)</div>
              <input data-testid="bc-form" type="url" value={editing.form} onChange={(e) => setEditing({...editing, form: e.target.value})} placeholder="https://www.spokeo.com/optout" className="brutal-input"/>
            </div>
            <button onClick={save} data-testid="bc-save" className="brutal-btn brutal-btn-primary flex items-center gap-2"><Save size={14}/>Save Contact</button>
            <Field label="Tip" value="Use email when the broker accepts removal requests via email (preferred). Use form URL when only a web form is available."/>
          </div>
        )}
      </Drawer>
    </div>
  );
}
