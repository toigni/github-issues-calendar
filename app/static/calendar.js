document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("/api/issues");
  const issues = await res.json();

  const events = issues.map(i => ({
    title: i.title,
    start: i.start,        // ← JSONにある start を使用
    url: i.url
  }));

  const calendar = new FullCalendar.Calendar(
    document.getElementById("calendar"),
    {
      initialView: "dayGridMonth",
      events: events,

      eventClick: function(info) {
        info.jsEvent.preventDefault(); // デフォルトのリンク動作を防止
        if (info.event.url) {
            window.open(info.event.url, "_blank");
        }
      }
    }
  );

  calendar.render();
});