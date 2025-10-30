(function () {
  function buildScale(tasks) {
    if (!tasks.length) {
      return { start: new Date(), end: new Date(), spanHours: 1 };
    }
    var start = new Date(tasks[0].start);
    var end = new Date(tasks[0].end);
    tasks.forEach(function (task) {
      var taskStart = new Date(task.start);
      var taskEnd = new Date(task.end);
      if (taskStart < start) start = taskStart;
      if (taskEnd > end) end = taskEnd;
    });
    var spanHours = Math.max(1, (end - start) / 36e5);
    return { start: start, end: end, spanHours: spanHours };
  }

  function renderSidebar(container, tasks) {
    container.innerHTML = "";
    tasks.forEach(function (task) {
      var wrapper = document.createElement("div");
      wrapper.className = "gantt-task-meta";
      wrapper.innerHTML = "<h6 class='mb-1'>" + task.name + "</h6>" +
        "<div class='text-muted small'>" +
        (task.workshop ? "Atelier : " + task.workshop + "<br>" : "") +
        (task.lead ? "Responsable : " + task.lead + "<br>" : "") +
        "Durée : " + task.duration_hours.toFixed(1) + " h</div>";
      container.appendChild(wrapper);
    });
  }

  function renderChart(container, tasks, scale) {
    var placeholder = container.querySelector("[data-role='placeholder']");
    if (placeholder) {
      placeholder.remove();
    }
    var width = Math.max(container.clientWidth, 600);
    var rowHeight = 36;
    var chartHeight = rowHeight * tasks.length + 40;
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", width);
    svg.setAttribute("height", chartHeight);

    var axisGroup = document.createElementNS(svg.namespaceURI, "g");
    axisGroup.setAttribute("class", "gantt-axis");
    var baseline = document.createElementNS(svg.namespaceURI, "line");
    baseline.setAttribute("x1", 0);
    baseline.setAttribute("y1", 20);
    baseline.setAttribute("x2", width);
    baseline.setAttribute("y2", 20);
    axisGroup.appendChild(baseline);

    var tickCount = Math.min(24, Math.max(6, Math.ceil(scale.spanHours / 8)));
    for (var i = 0; i <= tickCount; i++) {
      var ratio = i / tickCount;
      var tickX = ratio * width;
      var tick = document.createElementNS(svg.namespaceURI, "line");
      tick.setAttribute("x1", tickX);
      tick.setAttribute("y1", 15);
      tick.setAttribute("x2", tickX);
      tick.setAttribute("y2", chartHeight);
      tick.setAttribute("stroke-dasharray", "2 4");
      axisGroup.appendChild(tick);

      var tickLabel = document.createElementNS(svg.namespaceURI, "text");
      tickLabel.setAttribute("x", tickX + 4);
      tickLabel.setAttribute("y", 12);
      var tickDate = new Date(scale.start.getTime() + ratio * scale.spanHours * 36e5);
      tickLabel.textContent = tickDate.toLocaleString();
      axisGroup.appendChild(tickLabel);
    }
    svg.appendChild(axisGroup);

    tasks.forEach(function (task, index) {
      var startOffset = (new Date(task.start) - scale.start) / 36e5;
      var widthRatio = task.duration_hours / scale.spanHours;
      var barWidth = Math.max(8, widthRatio * width);
      var x = (startOffset / scale.spanHours) * width;
      var y = 40 + index * rowHeight;

      var bar = document.createElementNS(svg.namespaceURI, "rect");
      bar.setAttribute("x", x);
      bar.setAttribute("y", y);
      bar.setAttribute("width", barWidth);
      bar.setAttribute("height", rowHeight * 0.6);
      bar.setAttribute("rx", 4);
      bar.setAttribute("class", "gantt-bar " + (task.is_critical ? "critical" : "standard"));
      svg.appendChild(bar);

      var label = document.createElementNS(svg.namespaceURI, "text");
      label.setAttribute("x", x + 4);
      label.setAttribute("y", y + rowHeight * 0.35);
      label.setAttribute("fill", "#fff");
      label.setAttribute("font-size", "12");
      label.textContent = task.name;
      svg.appendChild(label);
    });

    container.innerHTML = "";
    container.appendChild(svg);
  }

  function render(root, payload) {
    var sidebar = root.querySelector("[data-role='sidebar']");
    var chart = root.querySelector("[data-role='chart']");
    var generatedAt = root.querySelector("[data-role='generated-at']");
    if (generatedAt) {
      generatedAt.textContent = "Données générées le " + new Date(payload.generated_at).toLocaleString();
    }
    renderSidebar(sidebar, payload.tasks);
    var scale = buildScale(payload.tasks);
    renderChart(chart, payload.tasks, scale);
  }

  function fetchData(root) {
    var endpoint = root.dataset.endpoint;
    if (!endpoint) return;
    fetch(endpoint)
      .then(function (response) {
        if (!response.ok) throw new Error("Impossible de récupérer les données du Gantt");
        return response.json();
      })
      .then(function (payload) {
        render(root, payload);
      })
      .catch(function (error) {
        console.error(error);
        var placeholder = root.querySelector("[data-role='placeholder']");
        if (placeholder) {
          placeholder.textContent = "Erreur lors du chargement : " + error.message;
        }
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("gantt-root");
    if (root) {
      fetchData(root);
    }
  });
})();
