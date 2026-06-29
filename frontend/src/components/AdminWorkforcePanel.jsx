import React, { useEffect, useState } from "react";
import adminApi from "@/lib/adminApi";

export default function AdminWorkforcePanel() {
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [shifts, setShifts] = useState([]);
  const [timesheets, setTimesheets] = useState([]);
  const [payrollRuns, setPayrollRuns] = useState([]);

  const [shiftForm, setShiftForm] = useState({ employee_id: "", employee_email: "", role: "support", location: "remote", start_at: "", end_at: "" });
  const [timesheetForm, setTimesheetForm] = useState({ employee_id: "", employee_email: "", date: "", hours: 8, overtime_hours: 0 });
  const [payrollForm, setPayrollForm] = useState({ period_start: "", period_end: "", total_gross: 0, total_net: 0 });

  const refresh = async () => {
    setLoading(true);
    setNotice("");
    try {
      const [s, t, p] = await Promise.all([
        adminApi.workforceAdminShifts(),
        adminApi.workforceAdminTimesheets(),
        adminApi.workforceAdminPayrollRuns(),
      ]);
      setShifts(s || []);
      setTimesheets(t || []);
      setPayrollRuns(p || []);
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to load workforce data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const createShift = async () => {
    try {
      const r = await adminApi.workforceAdminCreateShift(shiftForm);
      if (!r?.ok) return setNotice(r?.message || "Failed to create shift.");
      setShiftForm({ employee_id: "", employee_email: "", role: "support", location: "remote", start_at: "", end_at: "" });
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to create shift.");
    }
  };

  const createTimesheet = async () => {
    try {
      const r = await adminApi.workforceAdminCreateTimesheet(timesheetForm);
      if (!r?.ok) return setNotice(r?.message || "Failed to create timesheet.");
      setTimesheetForm({ employee_id: "", employee_email: "", date: "", hours: 8, overtime_hours: 0 });
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to create timesheet.");
    }
  };

  const createPayroll = async () => {
    try {
      const r = await adminApi.workforceAdminCreatePayrollRun({ ...payrollForm, line_items: [] });
      if (!r?.ok) return setNotice(r?.message || "Failed to create payroll run.");
      setPayrollForm({ period_start: "", period_end: "", total_gross: 0, total_net: 0 });
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to create payroll run.");
    }
  };

  const patchTimesheetStatus = async (id, approved) => {
    const r = await adminApi.workforceAdminPatchTimesheet(id, { approved });
    if (!r?.ok) return setNotice(r?.message || "Failed to update timesheet.");
    await refresh();
  };

  if (loading) return <div className="font-mono text-zinc-500">loading workforce<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-workforce-panel">
      {notice && <div className="brutal-card p-3 font-mono text-xs text-zinc-300">{notice}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="brutal-card p-4">
          <div className="overline mb-3">// create shift</div>
          <input className="brutal-input mb-2" placeholder="employee id" value={shiftForm.employee_id} onChange={(e) => setShiftForm({ ...shiftForm, employee_id: e.target.value })} />
          <input className="brutal-input mb-2" placeholder="employee email" value={shiftForm.employee_email} onChange={(e) => setShiftForm({ ...shiftForm, employee_email: e.target.value })} />
          <input className="brutal-input mb-2" placeholder="role" value={shiftForm.role} onChange={(e) => setShiftForm({ ...shiftForm, role: e.target.value })} />
          <input className="brutal-input mb-2" placeholder="location" value={shiftForm.location} onChange={(e) => setShiftForm({ ...shiftForm, location: e.target.value })} />
          <input className="brutal-input mb-2" type="datetime-local" value={shiftForm.start_at} onChange={(e) => setShiftForm({ ...shiftForm, start_at: e.target.value })} />
          <input className="brutal-input" type="datetime-local" value={shiftForm.end_at} onChange={(e) => setShiftForm({ ...shiftForm, end_at: e.target.value })} />
          <button className="brutal-btn mt-3 w-full" onClick={createShift}>Create Shift</button>
        </div>

        <div className="brutal-card p-4">
          <div className="overline mb-3">// create timesheet</div>
          <input className="brutal-input mb-2" placeholder="employee id" value={timesheetForm.employee_id} onChange={(e) => setTimesheetForm({ ...timesheetForm, employee_id: e.target.value })} />
          <input className="brutal-input mb-2" placeholder="employee email" value={timesheetForm.employee_email} onChange={(e) => setTimesheetForm({ ...timesheetForm, employee_email: e.target.value })} />
          <input className="brutal-input mb-2" type="date" value={timesheetForm.date} onChange={(e) => setTimesheetForm({ ...timesheetForm, date: e.target.value })} />
          <input className="brutal-input mb-2" type="number" placeholder="hours" value={timesheetForm.hours} onChange={(e) => setTimesheetForm({ ...timesheetForm, hours: e.target.value })} />
          <input className="brutal-input" type="number" placeholder="overtime" value={timesheetForm.overtime_hours} onChange={(e) => setTimesheetForm({ ...timesheetForm, overtime_hours: e.target.value })} />
          <button className="brutal-btn mt-3 w-full" onClick={createTimesheet}>Create Timesheet</button>
        </div>

        <div className="brutal-card p-4">
          <div className="overline mb-3">// create payroll run</div>
          <input className="brutal-input mb-2" type="date" value={payrollForm.period_start} onChange={(e) => setPayrollForm({ ...payrollForm, period_start: e.target.value })} />
          <input className="brutal-input mb-2" type="date" value={payrollForm.period_end} onChange={(e) => setPayrollForm({ ...payrollForm, period_end: e.target.value })} />
          <input className="brutal-input mb-2" type="number" placeholder="total gross" value={payrollForm.total_gross} onChange={(e) => setPayrollForm({ ...payrollForm, total_gross: e.target.value })} />
          <input className="brutal-input" type="number" placeholder="total net" value={payrollForm.total_net} onChange={(e) => setPayrollForm({ ...payrollForm, total_net: e.target.value })} />
          <button className="brutal-btn mt-3 w-full" onClick={createPayroll}>Create Payroll Run</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="brutal-card p-4">
          <div className="overline mb-3">// shifts</div>
          <div className="space-y-2 max-h-[360px] overflow-y-auto">
            {shifts.length === 0 && <div className="font-mono text-xs text-zinc-500">No shifts.</div>}
            {shifts.map((s) => (
              <div key={s.id} className="border border-[#222] p-2 font-mono text-xs">
                <div className="text-white">{s.employee_email || s.employee_id}</div>
                <div className="text-zinc-500">{s.role} · {s.location}</div>
                <div className="text-zinc-400">{String(s.start_at).slice(0, 16)} → {String(s.end_at).slice(0, 16)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="brutal-card p-4">
          <div className="overline mb-3">// timesheets</div>
          <div className="space-y-2 max-h-[360px] overflow-y-auto">
            {timesheets.length === 0 && <div className="font-mono text-xs text-zinc-500">No timesheets.</div>}
            {timesheets.map((t) => (
              <div key={t.id} className="border border-[#222] p-2 font-mono text-xs">
                <div className="text-white">{t.employee_email || t.employee_id}</div>
                <div className="text-zinc-500">{t.date} · {t.hours}h (+{t.overtime_hours}h OT)</div>
                <div className="mt-2 flex gap-2">
                  <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => patchTimesheetStatus(t.id, true)}>approve</button>
                  <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => patchTimesheetStatus(t.id, false)}>unapprove</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="brutal-card p-4">
        <div className="overline mb-3">// payroll runs</div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="text-left overline py-2">period</th>
                <th className="text-left overline py-2">status</th>
                <th className="text-left overline py-2">gross</th>
                <th className="text-left overline py-2">net</th>
              </tr>
            </thead>
            <tbody>
              {payrollRuns.length === 0 && <tr><td colSpan={4} className="py-2 font-mono text-xs text-zinc-500">No payroll runs.</td></tr>}
              {payrollRuns.map((p) => (
                <tr key={p.id} className="border-b border-[#222]">
                  <td className="py-2 font-mono text-xs">{p.period_start} → {p.period_end}</td>
                  <td className="py-2 font-mono text-xs text-zinc-400">{p.status}</td>
                  <td className="py-2 font-mono text-xs">${p.total_gross}</td>
                  <td className="py-2 font-mono text-xs">${p.total_net}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
