import React, { useMemo, useState } from "react";
import api from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const EMPTY_FORM = {
  businessName: "",
  address: "",
  privacyEmail: "",
  phone: "",
  country: "",
  lookupUrl: "",
  notes: "",
};

const CSV_HEADER_ALIASES = {
  businessName: ["business name", "business", "name", "broker", "broker name", "company"],
  address: ["address", "street", "location", "hq address"],
  privacyEmail: ["privacy email", "privacy department email", "email", "privacy dept email"],
  phone: ["phone", "phone number", "telephone", "tel"],
  country: ["country", "country code", "nation"],
  lookupUrl: ["lookup url", "search url", "scrape url", "discover url", "site url", "url", "broker url"],
  notes: ["notes", "note", "comments", "comment", "details"],
};

const BROKER_CSV_TEMPLATE = [
  "business name,address,privacy email,phone,country,lookup url,notes",
  "Example Broker Inc,123 Main St Toronto ON,privacy@examplebroker.com,+1-416-555-0100,Canada,https://examplebroker.com/search,Public people-search endpoint",
].join("\n");

function normalizeHeader(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function parseCsvLine(line) {
  const cells = [];
  let cur = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    const next = line[i + 1];
    if (ch === '"') {
      if (inQuotes && next === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === "," && !inQuotes) {
      cells.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  cells.push(cur.trim());
  return cells;
}

function resolveCsvMapping(headers) {
  const normalized = headers.map(normalizeHeader);
  const mapping = {};

  Object.entries(CSV_HEADER_ALIASES).forEach(([key, aliases]) => {
    const idx = normalized.findIndex((h) => aliases.includes(h));
    if (idx >= 0) mapping[key] = idx;
  });

  return mapping;
}

function parseBrokerCsv(text) {
  const lines = String(text || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((line) => line.trim().length > 0);

  if (lines.length < 2) {
    return { rows: [], errors: ["CSV must include a header row and at least one data row."] };
  }

  const headers = parseCsvLine(lines[0]);
  const mapping = resolveCsvMapping(headers);
  const missingHeaders = ["businessName", "address", "privacyEmail", "country"].filter((k) => mapping[k] == null);
  if (missingHeaders.length) {
    return {
      rows: [],
      errors: [
        `Missing required headers: ${missingHeaders.join(", ")}. Required: business name, address, privacy email, country.`,
      ],
    };
  }

  const rows = [];
  const errors = [];

  lines.slice(1).forEach((line, i) => {
    const cells = parseCsvLine(line);
    const rowNum = i + 2;
    const row = {
      businessName: cells[mapping.businessName] || "",
      address: cells[mapping.address] || "",
      privacyEmail: cells[mapping.privacyEmail] || "",
      phone: mapping.phone != null ? (cells[mapping.phone] || "") : "",
      country: cells[mapping.country] || "",
      lookupUrl: mapping.lookupUrl != null ? (cells[mapping.lookupUrl] || "") : "",
      notes: mapping.notes != null ? (cells[mapping.notes] || "") : "",
    };

    if (!row.businessName || !row.address || !row.privacyEmail || !row.country) {
      errors.push(`Row ${rowNum}: missing one or more required fields.`);
      return;
    }
    if (!String(row.privacyEmail).includes("@")) {
      errors.push(`Row ${rowNum}: privacy email appears invalid.`);
      return;
    }
    rows.push(row);
  });

  return { rows, errors };
}

function buildDescription(form, source) {
  return [
    `Source: ${source}`,
    `Business Name: ${form.businessName}`,
    `Address: ${form.address}`,
    `Privacy Email: ${form.privacyEmail}`,
    `Phone: ${form.phone || "N/A"}`,
    `Country: ${form.country}`,
    `Lookup/Search URL: ${form.lookupUrl || "N/A"}`,
    `Additional Notes: ${form.notes || "N/A"}`,
  ].join("\n");
}

function buildBulkDescription(rows, source) {
  const header = [`Source: ${source}`, `Submission Type: CSV bulk import`, `Total Brokers: ${rows.length}`, ""].join("\n");
  const blocks = rows.map((row, idx) => {
    return [
      `Broker ${idx + 1}`,
      `Business Name: ${row.businessName}`,
      `Address: ${row.address}`,
      `Privacy Email: ${row.privacyEmail}`,
      `Phone: ${row.phone || "N/A"}`,
      `Country: ${row.country}`,
      `Lookup/Search URL: ${row.lookupUrl || "N/A"}`,
      `Additional Notes: ${row.notes || "N/A"}`,
    ].join("\n");
  });
  return `${header}${blocks.join("\n\n")}`;
}

function openMailto(form, source) {
  const subject = encodeURIComponent(`Broker submission: ${form.businessName}`);
  const body = encodeURIComponent(buildDescription(form, source));
  window.location.href = `mailto:support@d31337m3.com?subject=${subject}&body=${body}`;
}

export default function BrokerSubmissionDialog({
  triggerLabel = "Submit Broker",
  triggerClassName = "brutal-btn",
  source = "public_landing",
  authenticated = false,
}) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [csvFileName, setCsvFileName] = useState("");
  const [csvRows, setCsvRows] = useState([]);
  const [csvErrors, setCsvErrors] = useState([]);
  const csvTemplateHref = useMemo(
    () => `data:text/csv;charset=utf-8,${encodeURIComponent(BROKER_CSV_TEMPLATE)}`,
    []
  );

  const canSubmit = useMemo(() => {
    if (csvRows.length > 0) return true;
    return Boolean(
      form.businessName.trim() &&
      form.address.trim() &&
      form.privacyEmail.trim() &&
      form.country.trim()
    );
  }, [form, csvRows]);

  const onChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit || submitting) return;

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const useCsv = csvRows.length > 0;
      const subject = useCsv
        ? `Broker submission (CSV): ${csvRows.length} brokers`
        : `Broker submission: ${form.businessName}`;
      const description = useCsv ? buildBulkDescription(csvRows, source) : buildDescription(form, source);

      if (!authenticated) {
        if (useCsv) {
          const encodedSubject = encodeURIComponent(subject);
          const encodedBody = encodeURIComponent(description);
          window.location.href = `mailto:support@d31337m3.com?subject=${encodedSubject}&body=${encodedBody}`;
        } else {
          openMailto(form, source);
        }
        setSuccess("Draft sent to support intake.");
        setOpen(false);
        setForm(EMPTY_FORM);
        setCsvFileName("");
        setCsvRows([]);
        setCsvErrors([]);
        return;
      }

      const payload = {
        subject,
        description,
        priority: "normal",
      };
      const response = await api.post("/support/tickets", payload);
      const ticketId = response?.data?.ticket?.id;
      setSuccess(ticketId ? `Submission received. Ticket: ${ticketId}` : "Submission received.");
      setOpen(false);
      setForm(EMPTY_FORM);
      setCsvFileName("");
      setCsvRows([]);
      setCsvErrors([]);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Unable to submit right now.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button type="button" className={triggerClassName} data-testid={`broker-submit-trigger-${source}`}>
            {triggerLabel}
          </button>
        </DialogTrigger>
        <DialogContent className="border border-[#222] bg-[#080808] text-white">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl">Submit New Broker</DialogTitle>
            <DialogDescription className="font-mono text-xs text-zinc-400">
              Add a broker we should track. Required fields are marked with *.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-3" onSubmit={onSubmit}>
            <div className="border border-[#222] bg-[#050505] p-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="overline">bulk csv upload (optional)</div>
                <a
                  href={csvTemplateHref}
                  download="broker_submission_template.csv"
                  className="font-mono text-[11px] text-[#00FF41] hover:text-white"
                  data-testid="broker-csv-template-download"
                >
                  Download Template CSV
                </a>
              </div>
              <input
                type="file"
                accept=".csv,text/csv"
                className="block w-full font-mono text-xs text-zinc-300 file:mr-3 file:border file:border-[#333] file:bg-[#111] file:px-3 file:py-1 file:text-xs file:text-zinc-200 hover:file:border-[#FF3333]"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  setCsvRows([]);
                  setCsvErrors([]);
                  setCsvFileName("");
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = () => {
                    const text = String(reader.result || "");
                    const parsed = parseBrokerCsv(text);
                    setCsvRows(parsed.rows);
                    setCsvErrors(parsed.errors);
                    setCsvFileName(file.name);
                  };
                  reader.onerror = () => {
                    setCsvErrors(["Could not read the selected CSV file."]);
                  };
                  reader.readAsText(file);
                }}
              />
              <div className="mt-2 font-mono text-[11px] text-zinc-500">
                Headers supported: business name, address, privacy email, phone, country, lookup url, notes.
              </div>
              {csvFileName && (
                <div className="mt-2 font-mono text-xs text-zinc-300">
                  File: {csvFileName} • Parsed rows: {csvRows.length}
                </div>
              )}
              {csvErrors.length > 0 && (
                <div className="mt-2 space-y-1 font-mono text-xs text-[#FF3333] max-h-28 overflow-auto">
                  {csvErrors.slice(0, 8).map((item) => (
                    <div key={item}>• {item}</div>
                  ))}
                  {csvErrors.length > 8 && <div>• +{csvErrors.length - 8} more errors</div>}
                </div>
              )}
              {csvRows.length > 0 && (
                <div className="mt-2 overflow-auto border border-[#222]">
                  <table className="w-full font-mono text-[11px]">
                    <thead className="bg-[#0e0e0e] text-zinc-400">
                      <tr>
                        <th className="text-left px-2 py-1">Business</th>
                        <th className="text-left px-2 py-1">Country</th>
                        <th className="text-left px-2 py-1">Privacy Email</th>
                      </tr>
                    </thead>
                    <tbody>
                      {csvRows.slice(0, 5).map((row, idx) => (
                        <tr key={`${row.businessName}-${idx}`} className="border-t border-[#1e1e1e] text-zinc-300">
                          <td className="px-2 py-1">{row.businessName}</td>
                          <td className="px-2 py-1">{row.country}</td>
                          <td className="px-2 py-1">{row.privacyEmail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {csvRows.length > 5 && <div className="px-2 py-1 font-mono text-[11px] text-zinc-500">Showing 5 of {csvRows.length} rows</div>}
                </div>
              )}
            </div>

            <div>
              <div className="overline mb-1">business name *</div>
              <input className="brutal-input" value={form.businessName} onChange={(e) => onChange("businessName", e.target.value)} required={csvRows.length === 0} />
            </div>

            <div>
              <div className="overline mb-1">address *</div>
              <input className="brutal-input" value={form.address} onChange={(e) => onChange("address", e.target.value)} required={csvRows.length === 0} />
            </div>

            <div>
              <div className="overline mb-1">privacy department email *</div>
              <input type="email" className="brutal-input" value={form.privacyEmail} onChange={(e) => onChange("privacyEmail", e.target.value)} required={csvRows.length === 0} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <div className="overline mb-1">phone</div>
                <input className="brutal-input" value={form.phone} onChange={(e) => onChange("phone", e.target.value)} />
              </div>
              <div>
                <div className="overline mb-1">country *</div>
                <input className="brutal-input" value={form.country} onChange={(e) => onChange("country", e.target.value)} required={csvRows.length === 0} />
              </div>
            </div>

            <div>
              <div className="overline mb-1">lookup/search/scrape url</div>
              <input type="url" className="brutal-input" placeholder="https://example.com/people-search" value={form.lookupUrl} onChange={(e) => onChange("lookupUrl", e.target.value)} />
            </div>

            <div>
              <div className="overline mb-1">additional notes</div>
              <textarea className="brutal-input min-h-[90px]" value={form.notes} onChange={(e) => onChange("notes", e.target.value)} />
            </div>

            {error && <div className="font-mono text-xs text-[#FF3333]">{error}</div>}
            {success && <div className="font-mono text-xs text-[#00FF41]">{success}</div>}

            <DialogFooter>
              <button type="submit" disabled={!canSubmit || submitting} className="brutal-btn brutal-btn-primary w-full sm:w-auto">
                {submitting ? "Submitting..." : "Submit Broker"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {success && !open && (
        <div className="mt-2 font-mono text-xs text-[#00FF41]" data-testid={`broker-submit-success-${source}`}>
          {success}
        </div>
      )}
    </>
  );
}
