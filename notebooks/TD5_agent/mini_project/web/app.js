const { createApp, ref, nextTick } = Vue;

createApp({
  setup() {
    const input = ref("");
    const sending = ref(false);
    const log = ref([]); // [{role: 'user'|'assistant', text} | {role: 'trace', calls: [...]}]

    async function send() {
      const message = input.value.trim();
      if (!message || sending.value) return;
      log.value.push({ role: "user", text: message });
      input.value = "";
      sending.value = true;
      await scrollToBottom();

      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        });
        const data = await res.json();
        if (!res.ok) {
          log.value.push({ role: "assistant", text: "Error: " + (data.error || res.statusText) });
        } else {
          if (data.trace && data.trace.length) {
            log.value.push({ role: "trace", calls: data.trace });
          }
          log.value.push({ role: "assistant", text: data.reply });
        }
      } catch (e) {
        log.value.push({ role: "assistant", text: "Error: " + e.message });
      } finally {
        sending.value = false;
        await scrollToBottom();
      }
    }

    async function reset() {
      await fetch("/reset", { method: "POST" });
      log.value = [];
    }

    async function scrollToBottom() {
      await nextTick();
      const el = document.getElementById("log");
      if (el) el.scrollTop = el.scrollHeight;
    }

    function formatArgs(call) {
      return JSON.stringify(call.input);
    }

    return { input, sending, log, send, reset, formatArgs };
  },
  template: `
    <div class="page">
      <header>
        <h1>🛠️ PIM Copilot</h1>
        <button class="reset" @click="reset" title="Start a new conversation">New chat</button>
      </header>

      <div id="log" class="log">
        <div v-if="!log.length" class="empty">
          Ask about the catalog, or paste a messy supplier blurb to add a product — e.g.
          <em>"Aurora X: flagship ANC over-ear headphones, 40h battery, USB-C, Bluetooth 5.3,
          midnight black or sand. Wholesale €149, retail €249. 12-month warranty, MOQ 50."</em>
        </div>

        <template v-for="(entry, i) in log" :key="i">
          <div v-if="entry.role === 'user'" class="bubble user">{{ entry.text }}</div>

          <div v-else-if="entry.role === 'trace'" class="trace">
            <div v-for="(call, j) in entry.calls" :key="j" class="tool-call">
              <span class="tool-name">🔧 {{ call.tool }}</span>
              <span class="tool-args">{{ formatArgs(call) }}</span>
              <details>
                <summary>result</summary>
                <pre>{{ call.output }}</pre>
              </details>
            </div>
          </div>

          <div v-else class="bubble assistant">{{ entry.text }}</div>
        </template>

        <div v-if="sending" class="bubble assistant thinking">thinking…</div>
      </div>

      <form class="composer" @submit.prevent="send">
        <input v-model="input" placeholder="Type a message..." :disabled="sending" autofocus>
        <button type="submit" :disabled="sending || !input.trim()">Send</button>
      </form>
    </div>
  `,
}).mount("#app");
