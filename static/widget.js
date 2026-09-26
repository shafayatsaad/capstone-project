(() => {
  const script = document.currentScript;
  if (!script) return;
  const api = new URL(script.src).origin;
  const widgetId = new URL(script.src).searchParams.get("id");
  if (!widgetId) return;

  const root = document.createElement("section");
  root.dataset.leadWidget = widgetId;
  root.style.cssText = "font:16px system-ui,sans-serif;max-width:380px;padding:20px;border:1px solid #d9e2f0;border-radius:14px;color:#18233a;background:#fff;box-shadow:0 8px 24px #152a4614";
  script.insertAdjacentElement("afterend", root);

  const showError = (message) => {
    root.querySelector("[data-status]").textContent = message;
  };
  fetch(`${api}/widgets/${encodeURIComponent(widgetId)}/config`)
    .then((response) => {
      if (!response.ok) throw new Error("This form is unavailable right now.");
      return response.json();
    })
    .then((config) => {
      const title = document.createElement("h2");
      title.textContent = config.title;
      title.style.cssText = "font-size:20px;margin:0 0 6px";
      root.append(title);
      if (config.description) {
        const description = document.createElement("p");
        description.textContent = config.description;
        root.append(description);
      }
      const form = document.createElement("form");
      form.style.cssText = "display:grid;gap:12px";
      const fields = config.fields.length ? config.fields : [{ name: "email", label: "Email", type: "email", required: true }];
      fields.forEach((field) => {
        const label = document.createElement("label");
        label.textContent = field.label;
        label.style.cssText = "display:grid;gap:5px;font-size:14px";
        const input = document.createElement(field.type === "textarea" ? "textarea" : "input");
        if (field.type !== "textarea") input.type = ["email", "tel"].includes(field.type) ? field.type : "text";
        input.name = field.name;
        input.required = Boolean(field.required);
        input.maxLength = 2000;
        input.style.cssText = "font:inherit;padding:10px;border:1px solid #b8c5d6;border-radius:8px";
        label.append(input);
        form.append(label);
      });
      const honeypot = document.createElement("input");
      honeypot.name = "hp_field";
      honeypot.tabIndex = -1;
      honeypot.autocomplete = "off";
      honeypot.setAttribute("aria-hidden", "true");
      honeypot.style.cssText = "position:absolute;left:-10000px;width:1px;height:1px";
      form.append(honeypot);
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = config.button_text;
      button.style.cssText = "font:inherit;font-weight:600;padding:11px;border:0;border-radius:8px;background:#3b63e6;color:#fff;cursor:pointer";
      form.append(button);
      const status = document.createElement("p");
      status.dataset.status = "";
      status.setAttribute("role", "status");
      status.style.cssText = "font-size:14px;margin:0";
      form.append(status);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        button.disabled = true;
        showError("");
        const values = Object.fromEntries(fields.map((field) => [field.name, String(new FormData(form).get(field.name) || "")]));
        try {
          const response = await fetch(`${api}/submissions`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ widget_id: widgetId, fields: values, hp_field: honeypot.value }),
          });
          if (!response.ok) throw new Error(response.status === 429 ? "Please wait a moment and try again." : "We could not send your request. Please try again.");
          form.reset();
          showError("Thanks! Your response has been received.");
        } catch (error) {
          showError(error.message || "Connection problem. Please try again.");
        } finally {
          button.disabled = false;
        }
      });
      root.append(form);
    })
    .catch((error) => {
      root.textContent = error.message;
    });
})();
