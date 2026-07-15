/**
 * script.js
 * ---------
 * Small progressive-enhancement script for the static preview page
 * (templates/index.html). It does NOT talk to any backend or the GPT-Neo
 * model — it simply types out a pre-written sample email to illustrate
 * what the live Streamlit app produces.
 *
 * The actual generation logic lives in the Python app (see app.py and
 * the src/ package) and requires `streamlit run app.py` to use.
 */

(function () {
  "use strict";

  var SAMPLE_TEXT =
    "I hope this message finds you well. I am delighted to invite you to " +
    "AI Summit 2025. It will start at 10 AM and feature sessions on " +
    "Responsible AI.\n\nWe would be honored to have you join us and would " +
    "welcome any thoughts you might like to share during the sessions.";

  var TYPE_SPEED_MS = 18;

  function typeInto(element, text, onDone) {
    element.textContent = "";
    var cursor = document.createElement("span");
    cursor.className = "cursor";
    element.appendChild(cursor);

    var i = 0;
    function step() {
      if (i < text.length) {
        cursor.insertAdjacentText("beforebegin", text.charAt(i));
        i += 1;
        window.setTimeout(step, TYPE_SPEED_MS);
      } else if (typeof onDone === "function") {
        onDone();
      }
    }
    step();
  }

  function runDemo() {
    var body = document.getElementById("letterBody");
    if (!body) return;
    typeInto(body, SAMPLE_TEXT);
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Only animate the typewriter once the preview section scrolls into
    // view, so it feels intentional rather than firing off-screen.
    var letterSection = document.getElementById("preview");
    var hasRun = false;

    if ("IntersectionObserver" in window && letterSection) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting && !hasRun) {
              hasRun = true;
              runDemo();
            }
          });
        },
        { threshold: 0.4 }
      );
      observer.observe(letterSection);
    } else {
      // Fallback for browsers without IntersectionObserver support.
      runDemo();
    }

    var replayBtn = document.getElementById("replayBtn");
    if (replayBtn) {
      replayBtn.addEventListener("click", runDemo);
    }
  });
})();
