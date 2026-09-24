const $ = (selector) => document.querySelector(selector);

const STORE_KEY = "ja-lead-hunter-v2";

const STATUS_LABELS = {
  new: "New",
  contacted: "Contacted",
  quoted: "Estimate sent",
  won: "Won",
  lost: "Not a fit"
};

let searchResults = [];
let leads = loadLeads();

function loadLeads() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
  } catch {
    return [];
  }
}

function persist() {
  localStorage.setItem(STORE_KEY, JSON.stringify(leads));
  renderDashboard();
  renderPipeline();
}

function esc(value = "") {
  return String(value ?? "").replace(
    /[&<>'"]/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;"
      })[character]
  );
}

function safeUrl(value) {
  if (!value) return "";

  try {
    const url = new URL(value);

    return ["http:", "https:"].includes(url.protocol)
      ? url.href
      : "";
  } catch {
    return "";
  }
}

function leadKey(lead) {
  return (
    lead.id ||
    `${lead.name}|${lead.address}`.toLowerCase()
  );
}

function nowDue(lead) {
  return (
    lead.followup &&
    new Date(lead.followup) <= new Date() &&
    !["won", "lost"].includes(lead.status)
  );
}

function formatDate(value) {
  if (!value) return "No follow-up set";

  const date = new Date(value);

  if (isNaN(date)) {
    return "No follow-up set";
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function toast(text) {
  const element = $("#toast");

  element.textContent = text;
  element.classList.add("show");

  clearTimeout(toast.timer);

  toast.timer = setTimeout(() => {
    element.classList.remove("show");
  }, 2200);
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }

  const textarea = document.createElement("textarea");

  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function callOpener(lead) {
  return `Hi, this is Alex with J&A Tree and Lawn Service. We help local organizations with tree removal, trimming, storm cleanup, and ongoing property maintenance. Who handles tree and grounds work for ${lead.name}, and would you be open to keeping our information on file for estimates or emergency service?`;
}

function followupMessage(lead) {
  return `Hi, this is Alex with J&A Tree and Lawn Service following up about tree and grounds work for ${lead.name}. I wanted to see whether you have any upcoming trimming, removal, storm cleanup, or property-maintenance needs we could estimate for you.`;
}

$("#search-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    const button = $("#search-button");
    const data = new FormData(event.currentTarget);

    $("#results-section").hidden = false;

    $("#results-section").scrollIntoView({
      behavior: "smooth"
    });

    $("#results").innerHTML = "";
    $("#search-message").className = "message";
    $("#search-message").textContent =
      "Searching nearby businesses…";

    button.disabled = true;
    button.querySelector("span").textContent =
      "Searching…";

    try {
      const query = new URLSearchParams(data);

      const response = await fetch(
        `/api/leads?${query}`
      );

      const payload = await response.json();

      if (!response.ok || !payload.success) {
        throw new Error(
          payload.error ||
            "The search could not be completed."
        );
      }

      searchResults = payload.results || [];

      $("#results-title").textContent =
        `${data.get("location")} prospects`;

      $("#search-message").textContent =
        searchResults.length
          ? `${searchResults.length} possible business leads found.`
          : "No results found. Try another city or business type.";

      $("#download-results").hidden =
        !searchResults.length;

      renderResults();
    } catch (error) {
      searchResults = [];

      $("#search-message").className =
        "message error";

      $("#search-message").textContent =
        error.message;
    } finally {
      button.disabled = false;

      button.querySelector("span").textContent =
        "Hunt local leads";
    }
  }
);

function renderResults() {
  const saved = new Set(leads.map(leadKey));

  $("#results").innerHTML = searchResults
    .map((lead, index) => {
      const url = safeUrl(lead.url);
      const isSaved = saved.has(leadKey(lead));

      const rating = lead.rating
        ? `${esc(lead.rating)} ★ · ${esc(
            lead.review_count || 0
          )} reviews`
        : "Not rated";

      const phone = lead.phone
        ? `<a class="phone" href="tel:${esc(
            lead.phone
          )}">${esc(lead.phone)}</a>`
        : `<span class="muted">Phone unavailable</span>`;

      const website = url
        ? `<a href="${esc(
            url
          )}" target="_blank" rel="noopener">
             Website / map
           </a>`
        : "";

      return `
        <article class="lead-card">
          <div class="lead-top">
            <span>
              ${String(index + 1).padStart(2, "0")}
            </span>

            <span>${rating}</span>
          </div>

          <h3>${esc(lead.name)}</h3>

          <p class="address">
            ${esc(
              lead.address || "Address unavailable"
            )}
          </p>

          ${phone}

          <div class="lead-links">
            ${website}

            <button
              type="button"
              data-copy="${index}"
            >
              Copy opener
            </button>
          </div>

          <button
            class="save-button ${
              isSaved ? "saved" : ""
            }"
            data-save="${index}"
            ${isSaved ? "disabled" : ""}
          >
            ${
              isSaved
                ? "Saved to pipeline"
                : "Save lead + follow up"
            }
          </button>
        </article>
      `;
    })
    .join("");
}

$("#results").addEventListener(
  "click",
  async (event) => {
    const copyButton =
      event.target.closest("[data-copy]");

    if (copyButton) {
      const lead =
        searchResults[
          Number(copyButton.dataset.copy)
        ];

      await copyText(callOpener(lead));
      toast("Call opener copied");
      return;
    }

    const saveButton =
      event.target.closest("[data-save]");

    if (!saveButton) return;

    const source =
      searchResults[
        Number(saveButton.dataset.save)
      ];

    const alreadySaved = leads.some(
      (lead) => leadKey(lead) === leadKey(source)
    );

    if (alreadySaved) return;

    const tomorrow = new Date(
      Date.now() + 86400000
    );

    tomorrow.setMinutes(0, 0, 0);

    leads.unshift({
      ...source,
      status: "new",
      contact: "",
      notes: "",
      followup: tomorrow.toISOString(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });

    persist();
    renderResults();

    toast(
      "Lead saved — follow-up set for tomorrow"
    );
  }
);

function renderDashboard() {
  $("#saved-count").textContent = leads.length;
  $("#metric-total").textContent = leads.length;

  $("#metric-due").textContent =
    leads.filter(nowDue).length;

  $("#metric-contacted").textContent =
    leads.filter(
      (lead) => lead.status === "contacted"
    ).length;

  $("#metric-won").textContent =
    leads.filter(
      (lead) => lead.status === "won"
    ).length;

  $(".metric.urgent").classList.toggle(
    "active",
    leads.some(nowDue)
  );
}

function renderPipeline() {
  const filter = $("#pipeline-filter").value;
  let list = [...leads];

  if (filter === "due") {
    list = list.filter(nowDue);
  } else if (filter !== "all") {
    list = list.filter(
      (lead) => lead.status === filter
    );
  }

  list.sort((first, second) => {
    if (nowDue(first) !== nowDue(second)) {
      return nowDue
