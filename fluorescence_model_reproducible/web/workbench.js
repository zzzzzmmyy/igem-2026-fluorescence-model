(function () {
  "use strict";

  // ================= model constants (must match model_0921.py / final_model_summary.json) =================
  const COEF_GFPC = 2.6363458858137393e-07;
  const COEF_MCHERRYC = -5.50412798458503e-06;
  const INTERCEPT = 0.19327294046955756;
  const CV_RESIDUAL_SD = 0.020230368391386134;
  const CI_MULT = 1.96;
  const TRAIN_RANGE_GFPC = [7547.666666666664, 3100443.6666666665];
  const TRAIN_RANGE_MCHERRYC = [208.66666666666663, 40345.666666666664];

  const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
  const COLS = Array.from({ length: 12 }, (_, i) => i + 1);
  const ALL_IDS = [];
  ROWS.forEach((r) => COLS.forEach((c) => ALL_IDS.push(r + c)));

  // ================= state =================
  const plate = {};           // id -> 'none' | 'test' | 'blank'
  ALL_IDS.forEach((id) => (plate[id] = "none"));
  let wellData = {};          // id -> { GFP_raw, mCherry_raw }
  let results = {};           // id -> computed result
  let mode = "design";        // 'design' | 'results'

  // ================= helpers =================
  const $ = (sel) => document.querySelector(sel);
  const wellEls = {};

  function mean(arr) { return arr.reduce((a, b) => a + b, 0) / arr.length; }

  function fmtNum(x, digits) {
    if (x === undefined || x === null || Number.isNaN(x)) return "-";
    if (Math.abs(x) >= 1000) return Math.round(x).toLocaleString("en-US");
    return x.toFixed(digits === undefined ? 3 : digits);
  }

  function fractionColor(f) {
    const c0 = [214, 51, 108];   // #d6336c  f=0
    const c1 = [235, 104, 52];   // #eb6834  f=0.5
    const c2 = [42, 157, 63];    // #2a9d3f  f=1
    const t = Math.min(1, Math.max(0, f));
    let rgb;
    if (t < 0.5) {
      const k = t / 0.5;
      rgb = c0.map((v, i) => Math.round(v + (c1[i] - v) * k));
    } else {
      const k = (t - 0.5) / 0.5;
      rgb = c1.map((v, i) => Math.round(v + (c2[i] - v) * k));
    }
    return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  }

  function textColorFor(rgbStr) {
    const m = rgbStr.match(/\d+/g).map(Number);
    const lum = (0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]) / 255;
    return lum > 0.62 ? "#1a2233" : "#ffffff";
  }

  // ================= plate grid rendering =================
  function buildGrid() {
    const grid = $("#plate-grid");
    grid.innerHTML = "";
    grid.appendChild(document.createElement("div")); // corner
    COLS.forEach((c) => {
      const el = document.createElement("div");
      el.className = "axis";
      el.textContent = c;
      grid.appendChild(el);
    });
    ROWS.forEach((r) => {
      const label = document.createElement("div");
      label.className = "axis";
      label.textContent = r;
      grid.appendChild(label);
      COLS.forEach((c) => {
        const id = r + c;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "well role-none";
        btn.dataset.id = id;
        btn.setAttribute("aria-label", "Well " + id);
        grid.appendChild(btn);
        wellEls[id] = btn;
      });
    });
  }

  function renderWell(id) {
    const el = wellEls[id];
    const role = plate[id];
    el.classList.remove("role-test", "role-blank", "nodata");
    el.innerHTML = "";
    let flag = null;

    if (mode === "design") {
      el.disabled = false;
      el.textContent = "";
      el.style.background = "";
      el.style.color = "";
      el.style.borderColor = "";
      if (role === "test") el.classList.add("role-test");
      if (role === "blank") el.classList.add("role-blank");
    } else {
      // results mode
      el.disabled = true;
      if (role === "blank") {
        el.classList.add("role-blank");
        el.textContent = "B";
        el.style.background = "";
        el.style.color = "";
      } else if (role === "test") {
        const r = results[id];
        if (r) {
          const bg = fractionColor(r.fraction_clipped);
          el.style.background = bg;
          el.style.borderColor = bg;
          el.style.color = textColorFor(bg);
          el.textContent = r.fraction_clipped.toFixed(2).replace(/^0\./, ".");
          if (r.out_of_range) flag = "!";
        } else {
          el.classList.add("nodata");
          el.textContent = "?";
        }
      } else {
        el.style.background = "";
        el.style.color = "";
        el.textContent = "";
      }
    }
    if (flag) {
      const f = document.createElement("span");
      f.className = "flag";
      f.textContent = flag;
      el.appendChild(f);
    }
  }

  function renderAllWells() { ALL_IDS.forEach(renderWell); }

  function updateCounts() {
    let t = 0, b = 0, n = 0;
    ALL_IDS.forEach((id) => { if (plate[id] === "test") t++; else if (plate[id] === "blank") b++; else n++; });
    $("#count-test").textContent = t;
    $("#count-blank").textContent = b;
    $("#count-empty").textContent = n;
    $("#btn-analyze").disabled = !(t > 0 && b > 0);
  }

  function showDetail(id) {
    const role = plate[id];
    const roleLabel = role === "test" ? "Test well" : role === "blank" ? "Blank well" : "Unused";
    const d = wellData[id];
    let html = `<span class="well-id">${id}</span> · ${roleLabel}`;
    const dl = [];
    if (d) {
      dl.push(["GFP_raw", fmtNum(d.GFP_raw)]);
      dl.push(["mCherry_raw", fmtNum(d.mCherry_raw)]);
    } else {
      dl.push(["Data", "Not uploaded / No data matched to this well"]);
    }
    if (mode === "results" && role === "test" && results[id]) {
      const r = results[id];
      dl.push(["GFPc", fmtNum(r.GFPc)]);
      dl.push(["mCherryc", fmtNum(r.mCherryc)]);
      dl.push(["Predicted fraction", r.fraction.toFixed(4)]);
      dl.push(["95% CI", `${r.ci_low.toFixed(3)} ~ ${r.ci_high.toFixed(3)}`]);
      dl.push(["Calibration range", r.out_of_range ? "Outside range (extrapolation; interpret with caution)" : "Within training range"]);
    }
    html += "<dl>" + dl.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("") + "</dl>";
    $("#detail-panel").innerHTML = html;
  }

  // ================= drag / click selection (pointer events) =================
  let pointerDown = false;
  let dragged = false;
  let startId = null;
  const touchedThisDrag = new Set();

  function cycleRole(id) {
    const cur = plate[id];
    plate[id] = cur === "none" ? "test" : cur === "test" ? "blank" : "none";
  }

  $("#plate-grid").addEventListener("pointerdown", (e) => {
    if (mode !== "design") return;
    const target = e.target.closest(".well");
    if (!target) return;
    pointerDown = true;
    dragged = false;
    startId = target.dataset.id;
    touchedThisDrag.clear();
    touchedThisDrag.add(startId);
    target.classList.add("dragging");
    try { target.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });

  $("#plate-grid").addEventListener("pointermove", (e) => {
    if (!pointerDown || mode !== "design") return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const well = el && el.closest ? el.closest(".well") : null;
    if (!well) return;
    const id = well.dataset.id;
    if (!touchedThisDrag.has(id)) {
      if (id !== startId) dragged = true;
      touchedThisDrag.add(id);
      well.classList.add("dragging");
    }
  });

  function endDrag(e) {
    if (!pointerDown) return;
    pointerDown = false;
    touchedThisDrag.forEach((id) => wellEls[id].classList.remove("dragging"));
    if (dragged) {
      touchedThisDrag.forEach((id) => { plate[id] = "test"; });
    } else if (startId) {
      cycleRole(startId);
    }
    touchedThisDrag.forEach(renderWell);
    updateCounts();
    if (startId) showDetail(startId);
    startId = null;
    dragged = false;
  }

  $("#plate-grid").addEventListener("pointerup", endDrag);
  $("#plate-grid").addEventListener("pointercancel", endDrag);

  $("#plate-grid").addEventListener("pointerover", (e) => {
    const well = e.target.closest(".well");
    if (well) showDetail(well.dataset.id);
  });

  // ================= toolbar actions =================
  $("#btn-clear").addEventListener("click", () => {
    ALL_IDS.forEach((id) => (plate[id] = "none"));
    renderAllWells();
    updateCounts();
  });

  $("#btn-example").addEventListener("click", () => {
    ALL_IDS.forEach((id) => {
      const col = parseInt(id.slice(1), 10);
      plate[id] = col === 12 ? "blank" : "test";
    });
    renderAllWells();
    updateCounts();
  });

  $("#btn-back-to-design").addEventListener("click", () => {
    mode = "design";
    $("#btn-back-to-design").hidden = true;
    $("#scale-legend").hidden = true;
    $("#legend-results-note").hidden = true;
    renderAllWells();
    $("#card-plate").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // ================= file upload / parsing =================
  function normalizeWellId(raw) {
    if (raw === null || raw === undefined) return null;
    const s = String(raw).trim().toUpperCase().replace(/\s+/g, "");
    const m = s.match(/^([A-H])0*(\d{1,2})$/);
    if (!m) return null;
    const col = parseInt(m[2], 10);
    if (col < 1 || col > 12) return null;
    return m[1] + col;
  }

  function findKey(row, candidates) {
    const keys = Object.keys(row);
    for (const cand of candidates) {
      const hit = keys.find((k) => k.replace(/[^a-z0-9]/gi, "").toLowerCase() === cand);
      if (hit) return hit;
    }
    return null;
  }

  function setUploadStatus(html, kind) {
    $("#upload-status").innerHTML = `<div class="banner ${kind}">${html}</div>`;
  }

  $("#file-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    file.arrayBuffer().then((buf) => {
      let wb;
      try {
        wb = XLSX.read(buf, { type: "array" });
      } catch (err) {
        setUploadStatus("Unable to parse this file. Please check that it is in .xlsx / .xls / .csv format.", "error");
        return;
      }
      const sheet = wb.Sheets[wb.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(sheet, { defval: null });
      if (!rows.length) {
        setUploadStatus("No data rows were found in this file.", "error");
        return;
      }
      const wellKey = findKey(rows[0], ["well", "\u5b54\u4f4d", "\u5b54", "wellid"]);
      const gfpKey = findKey(rows[0], ["gfpraw", "gfp"]);
      const mchKey = findKey(rows[0], ["mcherryraw", "mcherry", "cherryraw", "cherry"]);
      if (!wellKey || !gfpKey || !mchKey) {
        setUploadStatus("The <code>Well</code> / <code>GFP_raw</code> / <code>mCherry_raw</code> columns were not found. Please check the column headers.", "error");
        return;
      }
      wellData = {};
      let matched = 0, unmatched = 0;
      rows.forEach((row) => {
        const id = normalizeWellId(row[wellKey]);
        if (!id) { unmatched++; return; }
        const gfp = Number(row[gfpKey]);
        const mch = Number(row[mchKey]);
        if (Number.isNaN(gfp) || Number.isNaN(mch)) { unmatched++; return; }
        wellData[id] = { GFP_raw: gfp, mCherry_raw: mch };
        matched++;
      });

      const usedIds = ALL_IDS.filter((id) => plate[id] !== "none");
      const usedWithData = usedIds.filter((id) => wellData[id]);
      const missing = usedIds.filter((id) => !wellData[id]);

      let msg = `Read ${matched} data rows successfully; data was matched to ${usedWithData.length} of the ${usedIds.length} marked wells.`;
      let kind = "ok";
      if (missing.length) {
        msg += ` Wells missing data: ${missing.join(", ")}.`;
        kind = missing.length === usedIds.length ? "error" : "info";
      }
      if (unmatched) msg += ` Another ${unmatched} rows with unrecognized well IDs or readings were ignored.`;
      setUploadStatus(msg, kind);
      renderAllWells();
    });
  });

  // ================= template download =================
  function browserDownloadFallback(filename, data) {
    try {
      const blob = data instanceof Blob ? data : new Blob([data]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return true;
    } catch (err) {
      return false;
    }
  }

  async function saveDownload(filename, data) {
    if (!browserDownloadFallback(filename, data)) {
      setUploadStatus("The download could not be completed. Please try another browser.", "error");
    }
  }

  $("#btn-template").addEventListener("click", async () => {
    const rows = [["Well", "Role", "GFP_raw", "mCherry_raw"]];
    ALL_IDS.forEach((id) => {
      if (plate[id] === "none") return;
      rows.push([id, plate[id] === "test" ? "test" : "blank", "", ""]);
    });
    if (rows.length === 1) {
      setUploadStatus("Mark at least one well in Step 1 before downloading the template.", "error");
      return;
    }
    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws["!cols"] = [{ wch: 8 }, { wch: 8 }, { wch: 12 }, { wch: 12 }];
    const wbNew = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wbNew, ws, "plate_data");
    const out = XLSX.write(wbNew, { bookType: "xlsx", type: "array" });
    await saveDownload("plate_template.xlsx", out);
  });

  // ================= analysis =================
  function setAnalyzeStatus(html, kind) {
    $("#analyze-status").innerHTML = html ? `<div class="banner ${kind}">${html}</div>` : "";
  }

  $("#btn-analyze").addEventListener("click", () => {
    const blankIds = ALL_IDS.filter((id) => plate[id] === "blank" && wellData[id]);
    const testIds = ALL_IDS.filter((id) => plate[id] === "test" && wellData[id]);

    if (!blankIds.length) { setAnalyzeStatus("No blank wells have matching data; the background baseline cannot be calculated.", "error"); return; }
    if (!testIds.length) { setAnalyzeStatus("No test wells have matching data; prediction cannot proceed.", "error"); return; }

    const blankGfpMean = mean(blankIds.map((id) => wellData[id].GFP_raw));
    const blankMchMean = mean(blankIds.map((id) => wellData[id].mCherry_raw));

    results = {};
    testIds.forEach((id) => {
      const d = wellData[id];
      const gfpc = d.GFP_raw - blankGfpMean;
      const mchc = d.mCherry_raw - blankMchMean;
      const pred = COEF_GFPC * gfpc + COEF_MCHERRYC * mchc + INTERCEPT;
      const outOfRange = gfpc < TRAIN_RANGE_GFPC[0] || gfpc > TRAIN_RANGE_GFPC[1] ||
                          mchc < TRAIN_RANGE_MCHERRYC[0] || mchc > TRAIN_RANGE_MCHERRYC[1];
      results[id] = {
        GFPc: gfpc, mCherryc: mchc,
        fraction: pred,
        fraction_clipped: Math.min(1, Math.max(0, pred)),
        ci_low: pred - CI_MULT * CV_RESIDUAL_SD,
        ci_high: pred + CI_MULT * CV_RESIDUAL_SD,
        out_of_range: outOfRange,
      };
    });

    const skippedTest = ALL_IDS.filter((id) => plate[id] === "test" && !wellData[id]);
    let msg = `Analysis complete: predicted ${testIds.length} test wells using ${blankIds.length} blank wells (mean GFP ${fmtNum(blankGfpMean)}, mean mCherry ${fmtNum(blankMchMean)}).`;
    if (skippedTest.length) msg += ` ${skippedTest.length} test wells were skipped due to missing data: ${skippedTest.join(", ")}.`;
    setAnalyzeStatus(msg, "ok");

    mode = "results";
    $("#btn-back-to-design").hidden = false;
    $("#scale-legend").hidden = false;
    $("#legend-results-note").hidden = false;
    renderAllWells();

    const fracs = testIds.map((id) => results[id].fraction_clipped);
    const oorCount = testIds.filter((id) => results[id].out_of_range).length;
    $("#results-summary").hidden = false;
    $("#sum-n").textContent = testIds.length;
    $("#sum-mean").textContent = mean(fracs).toFixed(3);
    $("#sum-oor").textContent = oorCount;

    const tbody = $("#results-table tbody");
    tbody.innerHTML = "";
    testIds.slice().sort().forEach((id) => {
      const r = results[id];
      const d = wellData[id];
      const tr = document.createElement("tr");
      const statusPill = r.out_of_range
        ? '<span class="pill warn">! Extrapolation</span>'
        : '<span class="pill good">Within range</span>';
      tr.innerHTML = `
        <td>${id}</td>
        <td>${fmtNum(d.GFP_raw)}</td>
        <td>${fmtNum(d.mCherry_raw)}</td>
        <td>${fmtNum(r.GFPc)}</td>
        <td>${fmtNum(r.mCherryc)}</td>
        <td>${r.fraction.toFixed(4)}</td>
        <td>${r.ci_low.toFixed(3)} ~ ${r.ci_high.toFixed(3)}</td>
        <td>${statusPill}</td>`;
      tbody.appendChild(tr);
    });
    $("#results-table-wrap").hidden = false;
    $("#btn-export").hidden = false;

    $("#card-analyze").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  $("#btn-export").addEventListener("click", async () => {
    const header = ["Well", "GFP_raw", "mCherry_raw", "GFPc", "mCherryc", "fraction", "fraction_clipped", "ci_low", "ci_high", "out_of_calibration_range"];
    const lines = [header.join(",")];
    Object.keys(results).sort().forEach((id) => {
      const r = results[id];
      const d = wellData[id];
      lines.push([id, d.GFP_raw, d.mCherry_raw, r.GFPc, r.mCherryc, r.fraction, r.fraction_clipped, r.ci_low, r.ci_high, r.out_of_range].join(","));
    });
    await saveDownload("gfp_fraction_results.csv", lines.join("\n"));
  });

  const repositoryUrl = (window.WORKBENCH_CONFIG || {}).repositoryUrl || "";
  const sourceLink = document.querySelector("#wiki-source");
  if (/^https:\/\/gitlab\.igem\.org\/2026\/[^?#]+$/.test(repositoryUrl)) {
    sourceLink.href = repositoryUrl;
    sourceLink.hidden = false;
  }

  // ================= init =================
  buildGrid();
  $("#btn-example").click();
})();
