document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (event) => {
      if (window.innerWidth <= 760 && sidebar.classList.contains("open") &&
          !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove("open");
      }
    });
  }
});

function renderStatusChart(labels, values) {
  const canvas = document.getElementById("statusChart");
  if (!canvas || typeof Chart === "undefined") return;
  const palette = {"Pending":"#f47f9f","Processing":"#f7bd4c","On Delivery":"#76b7ed","Delivered":"#77c987","Cancelled":"#92929a"};
  new Chart(canvas, {
    type: "doughnut",
    data: { labels, datasets: [{ data: values, backgroundColor: labels.map(label => palette[label] || "#d9cbd1"), borderWidth: 0, hoverOffset: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: "66%", plugins: { legend: { display: false }, tooltip: { enabled: true } } }
  });
}
function renderSalesChart(labels, values) {
  const canvas = document.getElementById("salesChart");
  if (!canvas || typeof Chart === "undefined") return;
  new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label: "Sales (₱)", data: values, backgroundColor: "#c66d8d", borderRadius: 3, maxBarThickness: 18 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: context => "₱" + Number(context.raw).toLocaleString("en-PH", {minimumFractionDigits:2}) } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#8c7d85", font: { size: 9 } } },
        y: { beginAtZero: true, grid: { color: "#f2e9ed" }, ticks: { color: "#8c7d85", font: { size: 9 }, callback: value => "₱" + Number(value).toLocaleString("en-PH") } }
      }
    }
  });
}
