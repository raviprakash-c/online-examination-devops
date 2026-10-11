const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "/api";

let currentUser = null;
let activeExam = null;
let timerId = null;
let selectedAdminExamId = null;
let selectedAdminExamTitle = "";

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[char];
  });
}

function showMessage(text, type, targetId) {
  type = type || "success";
  targetId = targetId || "global-message";
  const target = $(targetId);
  if (!target) return;
  target.textContent = text;
  target.className = "message " + type;
  window.clearTimeout(target._timer);
  target._timer = window.setTimeout(function () {
    target.classList.add("hidden");
  }, 5000);
}

function setView(viewId) {
  ["auth-view", "student-view", "admin-view"].forEach(function (id) {
    $(id).classList.add("hidden");
  });
  $(viewId).classList.remove("hidden");
}

async function api(path, options) {
  options = options || {};
  const headers = Object.assign({"Content-Type":"application/json"}, options.headers || {});
  const response = await fetch(API_BASE + path, Object.assign({}, options, {
    credentials: "include",
    headers: headers
  }));
  const payload = await response.json().catch(function () { return {}; });
  if (!response.ok) {
    throw new Error(payload.error || payload.message || ("Request failed (" + response.status + ")"));
  }
  return payload;
}

function renderSession() {
  const area = $("session-area");
  if (!currentUser) {
    area.innerHTML = "";
    return;
  }
  area.innerHTML =
    "<span>Signed in as <strong>" +
    escapeHtml(currentUser.username) +
    "</strong> (" +
    escapeHtml(currentUser.role) +
    ")</span>" +
    '<button id="logout-btn" class="secondary small">Logout</button>';
  $("logout-btn").addEventListener("click", logout);
}

async function loadSession() {
  try {
    const payload = await api("/auth/me");
    currentUser = payload.user;
  } catch (_error) {
    currentUser = null;
  }
  renderSession();
  if (!currentUser) {
    setView("auth-view");
    return;
  }
  if (currentUser.role === "admin") {
    setView("admin-view");
    await loadAdminDashboard();
  } else {
    setView("student-view");
    await loadStudentDashboard();
  }
}

async function login(event) {
  event.preventDefault();
  try {
    const payload = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("login-email").value.trim(),
        password: $("login-password").value
      })
    });
    currentUser = payload.user;
    $("login-form").reset();
    renderSession();
    showMessage("Login successful.");
    await loadSession();
  } catch (error) {
    showMessage(error.message, "error", "auth-message");
  }
}

async function register(event) {
  event.preventDefault();
  try {
    const payload = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username: $("register-username").value.trim(),
        email: $("register-email").value.trim(),
        password: $("register-password").value
      })
    });
    $("register-form").reset();
    showMessage(payload.message + ". You can now log in.", "success", "auth-message");
  } catch (error) {
    showMessage(error.message, "error", "auth-message");
  }
}

async function logout() {
  try {
    await api("/auth/logout", {method:"POST"});
  } finally {
    currentUser = null;
    activeExam = null;
    window.clearInterval(timerId);
    renderSession();
    setView("auth-view");
  }
}

async function loadStudentDashboard() {
  await Promise.all([loadStudentExams(), loadStudentResults()]);
}

async function loadStudentExams() {
  const container = $("student-exams");
  try {
    const payload = await api("/exams");
    const exams = payload.exams || [];
    if (!exams.length) {
      container.innerHTML = '<p class="muted">No exams have been created yet.</p>';
      return;
    }
    let html = "<table><thead><tr><th>Title</th><th>Description</th><th>Duration</th><th>Action</th></tr></thead><tbody>";
    exams.forEach(function (exam) {
      html += "<tr><td><strong>" + escapeHtml(exam.title) + "</strong></td>" +
        "<td>" + escapeHtml(exam.description || "-") + "</td>" +
        "<td>" + exam.duration_minutes + " min</td>" +
        '<td><button class="small start-exam-btn" data-id="' + exam.id + '">Start</button></td></tr>';
    });
    html += "</tbody></table>";
    container.innerHTML = html;
    container.querySelectorAll(".start-exam-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        startExam(Number(button.dataset.id));
      });
    });
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function startExam(examId) {
  window.clearInterval(timerId);
  try {
    const payload = await api("/exams/" + examId + "/start", {method:"POST"});
    activeExam = payload;
    activeExam.remainingSeconds = payload.exam.duration_minutes * 60;
    $("exam-title").textContent = payload.exam.title;
    $("exam-description").textContent = payload.exam.description || "";
    renderExamQuestions(payload.questions || []);
    $("exam-view").classList.remove("hidden");
    $("exam-view").scrollIntoView({behavior:"smooth", block:"start"});
    updateTimer();
    timerId = window.setInterval(updateTimer, 1000);
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function renderExamQuestions(questions) {
  const container = $("exam-questions");
  if (!questions.length) {
    container.innerHTML = '<p class="muted">This exam has no questions yet.</p>';
    return;
  }
  let html = "";
  questions.forEach(function (question, index) {
    html += '<div class="question-card">' +
      "<p><strong>Q" + (index + 1) + ". " + escapeHtml(question.question_text) +
      "</strong> <span class=\"muted\">(" + question.marks + " mark(s))</span></p>";
    ["a","b","c","d"].forEach(function (option) {
      html += '<label class="option"><input type="radio" name="question-' +
        question.id + '" value="' + option + '">' +
        "<span><strong>" + option.toUpperCase() + ".</strong> " +
        escapeHtml(question["option_" + option]) + "</span></label>";
    });
    html += "</div>";
  });
  container.innerHTML = html;
}

function updateTimer() {
  if (!activeExam) return;
  activeExam.remainingSeconds -= 1;
  const remaining = Math.max(activeExam.remainingSeconds, 0);
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");
  $("exam-timer").textContent = minutes + ":" + seconds;
  if (remaining <= 0) {
    window.clearInterval(timerId);
    submitExam(true);
  }
}

async function submitExam(autoSubmit) {
  if (!activeExam) return;
  if (!autoSubmit && !window.confirm("Submit this exam now?")) return;

  const answers = [];
  document.querySelectorAll("#exam-questions .question-card").forEach(function (card) {
    const firstRadio = card.querySelector('input[type="radio"]');
    if (!firstRadio) return;
    const selected = card.querySelector('input[type="radio"]:checked');
    answers.push({
      question_id: Number(firstRadio.name.replace("question-", "")),
      selected_option: selected ? selected.value : null
    });
  });

  try {
    const payload = await api("/attempts/" + activeExam.attempt.id + "/submit", {
      method: "POST",
      body: JSON.stringify({answers: answers})
    });
    window.clearInterval(timerId);
    $("exam-view").classList.add("hidden");
    const result = payload.result;
    activeExam = null;
    showMessage(
      "Exam submitted. Score: " + result.score + "/" + result.total_marks +
      " (" + result.percentage + "%). " + result.status +
      (autoSubmit ? ". Time expired." : ".")
    );
    await loadStudentResults();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadStudentResults() {
  const container = $("student-results");
  try {
    const payload = await api("/results");
    const results = payload.results || [];
    if (!results.length) {
      container.innerHTML = '<p class="muted">No submitted attempts yet.</p>';
      return;
    }
    let html = "<table><thead><tr><th>Exam</th><th>Score</th><th>Percentage</th><th>Status</th><th>Submitted</th></tr></thead><tbody>";
    results.forEach(function (result) {
      html += "<tr><td>" + escapeHtml(result.title) + "</td>" +
        "<td>" + result.score + " / " + result.total_marks + "</td>" +
        "<td>" + result.percentage + "%</td>" +
        '<td><span class="badge ' + String(result.status).toLowerCase() + '">' + result.status + "</span></td>" +
        "<td>" + escapeHtml(result.submitted_at || "-") + "</td></tr>";
    });
    html += "</tbody></table>";
    container.innerHTML = html;
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadAdminDashboard() {
  try {
    const values = await Promise.all([api("/exams"), api("/admin/results")]);
    const exams = values[0].exams || [];
    const results = values[1].results || [];
    const passCount = results.filter(function (r) { return r.status === "PASS"; }).length;
    const failCount = results.filter(function (r) { return r.status === "FAIL"; }).length;

    $("admin-stats").innerHTML =
      '<div class="stat"><div class="muted">Exams</div><div class="value">' + exams.length + "</div></div>" +
      '<div class="stat"><div class="muted">Submissions</div><div class="value">' + results.length + "</div></div>" +
      '<div class="stat"><div class="muted">Passed</div><div class="value">' + passCount + "</div></div>" +
      '<div class="stat"><div class="muted">Failed</div><div class="value">' + failCount + "</div></div>";

    renderAdminExams(exams);
    renderAdminResults(results);
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function renderAdminExams(exams) {
  const container = $("admin-exams");
  if (!exams.length) {
    container.innerHTML = '<p class="muted">No exams found.</p>';
    return;
  }
  let html = "<table><thead><tr><th>Title</th><th>Duration</th><th>Created</th><th>Actions</th></tr></thead><tbody>";
  exams.forEach(function (exam) {
    html += "<tr><td><strong>" + escapeHtml(exam.title) + "</strong><br><span class=\"muted\">" +
      escapeHtml(exam.description || "") + "</span></td>" +
      "<td>" + exam.duration_minutes + " min</td>" +
      "<td>" + escapeHtml(exam.created_at || "-") + "</td>" +
      '<td><div class="actions">' +
      '<button class="small question-btn" data-id="' + exam.id + '" data-title="' + escapeHtml(exam.title) + '">Questions</button>' +
      '<button class="small secondary edit-exam-btn" data-id="' + exam.id + '">Edit</button>' +
      '<button class="small danger delete-exam-btn" data-id="' + exam.id + '">Delete</button>' +
      "</div></td></tr>";
  });
  html += "</tbody></table>";
  container.innerHTML = html;

  container.querySelectorAll(".question-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      openQuestionManager(Number(button.dataset.id), button.dataset.title);
    });
  });
  container.querySelectorAll(".edit-exam-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      const exam = exams.find(function (item) { return item.id === Number(button.dataset.id); });
      if (exam) editExam(exam);
    });
  });
  container.querySelectorAll(".delete-exam-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      deleteExam(Number(button.dataset.id));
    });
  });
}

async function editExam(exam) {
  const title = window.prompt("Exam title:", exam.title);
  if (title === null) return;
  const duration = window.prompt("Duration in minutes:", exam.duration_minutes);
  if (duration === null) return;
  const description = window.prompt("Description:", exam.description || "");
  if (description === null) return;

  try {
    await api("/exams/" + exam.id, {
      method: "PUT",
      body: JSON.stringify({
        title: title,
        description: description,
        duration_minutes: Number(duration)
      })
    });
    showMessage("Exam updated.");
    await loadAdminDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deleteExam(examId) {
  if (!window.confirm("Delete this exam and its questions?")) return;
  try {
    await api("/exams/" + examId, {method:"DELETE"});
    if (selectedAdminExamId === examId) closeQuestionManager();
    showMessage("Exam deleted.");
    await loadAdminDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function openQuestionManager(examId, title) {
  selectedAdminExamId = examId;
  selectedAdminExamTitle = title;
  $("question-exam-title").textContent = title;
  $("question-manager").classList.remove("hidden");
  await loadAdminQuestions();
  $("question-manager").scrollIntoView({behavior:"smooth", block:"start"});
}

function closeQuestionManager() {
  selectedAdminExamId = null;
  selectedAdminExamTitle = "";
  $("question-manager").classList.add("hidden");
  $("question-create-form").reset();
}

async function loadAdminQuestions() {
  if (!selectedAdminExamId) return;
  try {
    const payload = await api("/exams/" + selectedAdminExamId + "/questions");
    const questions = payload.questions || [];
    if (!questions.length) {
      $("admin-questions").innerHTML = '<p class="muted">No questions yet.</p>';
      return;
    }

    let html = "<table><thead><tr><th>Question</th><th>Options</th><th>Correct</th><th>Marks</th><th>Actions</th></tr></thead><tbody>";
    questions.forEach(function (q) {
      html += "<tr><td>" + escapeHtml(q.question_text) + "</td>" +
        "<td>A: " + escapeHtml(q.option_a) + "<br>B: " + escapeHtml(q.option_b) +
        "<br>C: " + escapeHtml(q.option_c) + "<br>D: " + escapeHtml(q.option_d) + "</td>" +
        "<td>" + escapeHtml(String(q.correct_option).toUpperCase()) + "</td>" +
        "<td>" + q.marks + "</td>" +
        '<td><div class="actions"><button class="small edit-question-btn" data-id="' + q.id + '">Edit</button><button class="small danger delete-question-btn" data-id="' + q.id + '">Delete</button></div></td></tr>';
    });
    html += "</tbody></table>";
    $("admin-questions").innerHTML = html;

    $("admin-questions").querySelectorAll(".edit-question-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        const question = questions.find(function (item) { return item.id === Number(button.dataset.id); });
        if (question) editQuestion(question);
      });
    });
    $("admin-questions").querySelectorAll(".delete-question-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        deleteQuestion(Number(button.dataset.id));
      });
    });
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function editQuestion(question) {
  if (!selectedAdminExamId) return;
  const questionText = window.prompt("Question:", question.question_text);
  if (questionText === null) return;
  const optionA = window.prompt("Option A:", question.option_a);
  if (optionA === null) return;
  const optionB = window.prompt("Option B:", question.option_b);
  if (optionB === null) return;
  const optionC = window.prompt("Option C:", question.option_c);
  if (optionC === null) return;
  const optionD = window.prompt("Option D:", question.option_d);
  if (optionD === null) return;
  const correct = window.prompt("Correct option (a/b/c/d):", question.correct_option);
  if (correct === null) return;
  const marks = window.prompt("Marks:", question.marks);
  if (marks === null) return;

  try {
    await api("/exams/" + selectedAdminExamId + "/questions/" + question.id, {
      method: "PUT",
      body: JSON.stringify({
        question_text: questionText,
        option_a: optionA,
        option_b: optionB,
        option_c: optionC,
        option_d: optionD,
        correct_option: correct.toLowerCase(),
        marks: Number(marks)
      })
    });
    showMessage("Question updated.");
    await loadAdminQuestions();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deleteQuestion(questionId) {
  if (!selectedAdminExamId || !window.confirm("Delete this question?")) return;
  try {
    await api("/exams/" + selectedAdminExamId + "/questions/" + questionId, {method:"DELETE"});
    showMessage("Question deleted.");
    await loadAdminQuestions();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function renderAdminResults(results) {
  const container = $("admin-results");
  if (!results.length) {
    container.innerHTML = '<p class="muted">No student submissions yet.</p>';
    return;
  }
  let html = "<table><thead><tr><th>Student</th><th>Exam</th><th>Score</th><th>Percentage</th><th>Status</th><th>Submitted</th></tr></thead><tbody>";
  results.forEach(function (result) {
    html += "<tr><td>" + escapeHtml(result.username) + "<br><span class=\"muted\">" +
      escapeHtml(result.email) + "</span></td>" +
      "<td>" + escapeHtml(result.title) + "</td>" +
      "<td>" + result.score + " / " + result.total_marks + "</td>" +
      "<td>" + result.percentage + "%</td>" +
      '<td><span class="badge ' + String(result.status).toLowerCase() + '">' + result.status + "</span></td>" +
      "<td>" + escapeHtml(result.submitted_at || "-") + "</td></tr>";
  });
  html += "</tbody></table>";
  container.innerHTML = html;
}

async function createExam(event) {
  event.preventDefault();
  try {
    await api("/exams", {
      method: "POST",
      body: JSON.stringify({
        title: $("exam-title-input").value.trim(),
        description: $("exam-description-input").value.trim(),
        duration_minutes: Number($("exam-duration-input").value)
      })
    });
    $("exam-create-form").reset();
    showMessage("Exam created.");
    await loadAdminDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function createQuestion(event) {
  event.preventDefault();
  if (!selectedAdminExamId) {
    showMessage("Select an exam first.", "error");
    return;
  }
  try {
    await api("/exams/" + selectedAdminExamId + "/questions", {
      method: "POST",
      body: JSON.stringify({
        question_text: $("question-text-input").value.trim(),
        option_a: $("option-a-input").value.trim(),
        option_b: $("option-b-input").value.trim(),
        option_c: $("option-c-input").value.trim(),
        option_d: $("option-d-input").value.trim(),
        correct_option: $("correct-option-input").value,
        marks: Number($("question-marks-input").value)
      })
    });
    $("question-create-form").reset();
    showMessage("Question added.");
    await loadAdminQuestions();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

$("login-form").addEventListener("submit", login);
$("register-form").addEventListener("submit", register);
$("exam-form").addEventListener("submit", function (event) {
  event.preventDefault();
  submitExam(false);
});
$("student-refresh").addEventListener("click", loadStudentDashboard);
$("admin-refresh").addEventListener("click", loadAdminDashboard);
$("exam-create-form").addEventListener("submit", createExam);
$("question-create-form").addEventListener("submit", createQuestion);
$("close-question-manager").addEventListener("click", closeQuestionManager);

loadSession();
