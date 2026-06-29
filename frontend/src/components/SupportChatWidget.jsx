import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { MessageCircle, Send, X, TicketPlus } from "lucide-react";

export default function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [msgText, setMsgText] = useState("");
  const [ticketSubject, setTicketSubject] = useState("");
  const [ticketDesc, setTicketDesc] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const loadMyChat = async () => {
    const r = await api.get("/support/chats/me");
    setChat(r.data.chat || null);
    setMessages(r.data.messages || []);
  };

  useEffect(() => {
    if (!open) return;
    loadMyChat().catch(() => setNotice("Support chat unavailable right now."));
  }, [open]);

  const startChat = async () => {
    setBusy(true);
    setNotice("");
    try {
      const r = await api.post("/support/chats/me/start", {});
      setChat(r.data.chat || null);
      setMessages(r.data.messages || []);
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to start support chat.");
    } finally {
      setBusy(false);
    }
  };

  const sendMessage = async () => {
    if (!chat?.id || !msgText.trim()) return;
    setBusy(true);
    setNotice("");
    try {
      await api.post(`/support/chats/${chat.id}/messages`, { text: msgText.trim() });
      setMsgText("");
      await loadMyChat();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to send message.");
    } finally {
      setBusy(false);
    }
  };

  const createTicket = async () => {
    if (!ticketSubject.trim()) {
      setNotice("Ticket subject is required.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      await api.post("/support/tickets", {
        subject: ticketSubject.trim(),
        description: ticketDesc.trim(),
        chat_id: chat?.id || null,
      });
      setTicketSubject("");
      setTicketDesc("");
      setNotice("Ticket created and linked to your support chat.");
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to create ticket.");
    } finally {
      setBusy(false);
    }
  };

  const unreadHint = useMemo(() => {
    if (!messages.length) return "";
    const last = messages[messages.length - 1];
    return last?.sender_role === "admin" ? "New reply" : "";
  }, [messages]);

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 brutal-btn brutal-btn-primary !rounded-full !w-14 !h-14 flex items-center justify-center"
        title="Support Chat"
        data-testid="support-chat-toggle"
      >
        {open ? <X size={18} /> : <MessageCircle size={18} />}
      </button>

      {!open ? null : (
        <div className="fixed bottom-24 right-6 z-50 w-[360px] max-w-[calc(100vw-24px)] brutal-card p-4 bg-[#0b0b0b]" data-testid="support-chat-panel">
          <div className="flex items-center justify-between mb-3">
            <div className="overline">// support chat</div>
            {unreadHint && <span className="font-mono text-[10px] text-[#FFD700]">{unreadHint}</span>}
          </div>

          {!chat ? (
            <button className="brutal-btn brutal-btn-primary w-full" onClick={startChat} disabled={busy}>
              {busy ? "STARTING..." : "Start Support Chat"}
            </button>
          ) : (
            <>
              <div className="h-44 overflow-y-auto border border-[#222] p-2 mb-3 bg-black/50">
                {messages.length === 0 && <div className="font-mono text-xs text-zinc-500">No messages yet.</div>}
                {messages.map((m) => (
                  <div key={m.id} className="mb-2">
                    <div className="font-mono text-[10px] text-zinc-500">{m.sender_role?.toUpperCase()} · {String(m.sent_at || "").slice(0, 19)}</div>
                    <div className="font-mono text-xs text-zinc-200 whitespace-pre-wrap">{m.text}</div>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 mb-3">
                <input
                  className="brutal-input flex-1"
                  placeholder="Type a message"
                  value={msgText}
                  onChange={(e) => setMsgText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                />
                <button className="brutal-btn !px-3" onClick={sendMessage} disabled={busy || !msgText.trim()}><Send size={14} /></button>
              </div>

              <div className="border-t border-[#222] pt-3">
                <div className="font-mono text-xs text-zinc-400 mb-2 flex items-center gap-2"><TicketPlus size={12} /> Open ticket from this chat</div>
                <input
                  className="brutal-input mb-2"
                  placeholder="Ticket subject"
                  value={ticketSubject}
                  onChange={(e) => setTicketSubject(e.target.value)}
                />
                <textarea
                  className="brutal-input min-h-[72px]"
                  placeholder="Issue details"
                  value={ticketDesc}
                  onChange={(e) => setTicketDesc(e.target.value)}
                />
                <button className="brutal-btn mt-2 w-full" onClick={createTicket} disabled={busy}>Create Linked Ticket</button>
              </div>
            </>
          )}

          {notice && <div className="mt-2 font-mono text-xs text-zinc-400">{notice}</div>}
        </div>
      )}
    </>
  );
}
