import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import PageBrandBanner from "@/components/PageBrandBanner";
import SignaturePad from "@/components/SignaturePad";
import api from "@/lib/api";
import { PenLine, FileSignature } from "lucide-react";

export default function ProfileSignature() {
  const [tab, setTab] = useState("profile");
  const [signature, setSignature] = useState(null);
  const [sigName, setSigName] = useState("");
  const [profile, setProfile] = useState({ country: "CA", state: "ON", address: "", phone: "", name: "" });
  const [countries, setCountries] = useState({});

  const load = async () => {
    const [s, p, c] = await Promise.allSettled([
      api.get("/signature"),
      api.get("/profile"),
      api.get("/countries"),
    ]);

    const fallbackProfile = { country: "CA", state: "ON", address: "", phone: "", name: "" };
    const loadedProfile = p.status === "fulfilled" ? (p.value?.data?.profile || fallbackProfile) : fallbackProfile;
    setProfile(loadedProfile);
    setCountries(c.status === "fulfilled" ? (c.value?.data?.countries || {}) : {});
    setSignature(s.status === "fulfilled" ? (s.value?.data?.signature || null) : null);
    setSigName((s.status === "fulfilled" ? s.value?.data?.signature?.full_name : "") || loadedProfile?.name || "");
  };

  useEffect(() => { load(); }, []);

  const saveSignature = async (dataUrl) => {
    try {
      await api.post("/signature", { data_url: dataUrl, full_name: sigName });
      await load();
    } catch (e) {
      throw new Error(e?.response?.data?.detail || e?.message || "Failed to save signature");
    }
  };

  const saveProfile = async () => {
    try {
      await api.put("/profile", profile);
      alert("Profile updated.");
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || e?.message || "Failed to update profile.");
    }
  };

  return (
    <DashboardLayout title="Profile & Signature">
      <PageBrandBanner title="profile & signature" description="Manage your legal identity details and e-signature used in document workflows." />

      <div className="flex gap-2 mb-6" data-testid="profile-signature-tabs">
        {[ ["profile", "Profile"], ["signature", "Signature"] ].map(([k, l]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            data-testid={`profile-signature-tab-${k}`}
            className={`font-mono text-xs px-4 py-2 border ${tab===k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"}`}
          >
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="brutal-card p-6 max-w-2xl" data-testid="profile-panel">
          <div className="overline mb-4">// personal info (used in legal documents)</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="overline mb-1">full legal name</div>
              <input data-testid="profile-name" value={profile.name || ""} onChange={(e)=>setProfile({...profile, name: e.target.value})} className="brutal-input" />
            </div>
            <div>
              <div className="overline mb-1">phone</div>
              <input data-testid="profile-phone" value={profile.phone || ""} onChange={(e)=>setProfile({...profile, phone: e.target.value})} className="brutal-input" />
            </div>
            <div className="md:col-span-2">
              <div className="overline mb-1">street address</div>
              <input data-testid="profile-address" value={profile.address || ""} onChange={(e)=>setProfile({...profile, address: e.target.value})} className="brutal-input" />
            </div>
            <div>
              <div className="overline mb-1">country</div>
              <select data-testid="profile-country" value={profile.country || "CA"} onChange={(e)=>setProfile({...profile, country: e.target.value, state: ""})} className="brutal-input">
                {Object.entries(countries).map(([code, country]) => <option key={code} value={code}>{country.name}</option>)}
              </select>
            </div>
            <div>
              <div className="overline mb-1">state / province</div>
              <select data-testid="profile-state" value={profile.state || ""} onChange={(e)=>setProfile({...profile, state: e.target.value})} className="brutal-input">
                <option value="">—</option>
                {(countries[profile.country]?.states || []).map(state => <option key={state} value={state}>{state}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-3 font-mono text-xs text-zinc-500">
            Privacy law applicable to your jurisdiction: <span className="text-white">{countries[profile.country]?.privacy_law}</span>
          </div>
          <button onClick={saveProfile} data-testid="profile-save" className="brutal-btn brutal-btn-primary mt-5 flex items-center gap-2"><PenLine size={14}/>Save Profile</button>
        </div>
      )}

      {tab === "signature" && (
        <div className="space-y-4" data-testid="signature-panel">
          <div className="brutal-card p-4 border-[#A855F7]/40 bg-[#120f1f]/30">
            <div className="font-mono text-xs text-zinc-300 flex items-center gap-2">
              <FileSignature size={14} className="text-[#A855F7]" />
              This signature is affixed to legal notices when you sign documents.
            </div>
          </div>
          <SignaturePad onSave={saveSignature} fullName={sigName} setFullName={setSigName} existing={signature} />
        </div>
      )}
    </DashboardLayout>
  );
}