if (document.getElementById("editor") && window.hasOwnProperty("ace")) {
  var map = {
    'c': 'c_cpp',
    'c11': 'c_cpp',
    'cpp98': 'c_cpp',
    'cpp': 'c_cpp',
    'cpp14': 'c_cpp',
    'cc14': 'c_cpp',
    'csharp': 'csharp',
    'python2': 'python',
    'python': 'python',
    'java': 'java',
    'php': 'php',
    'fortran': 'fortran',
    'perl': 'perl',
    'ruby': 'ruby',
    'objc': 'objectivec',
    'haskell': 'haskell',
    'scala': 'scala',
    'lua': 'lua',
    'lisp': 'lisp',
    'js': 'javascript',
    'go': 'golang',
    'ocaml': 'ocaml',
    'fsharp': 'text',
    'pypy2': 'python',
    'swift': 'swift',
    'pascal': 'pascal',
    'rust': 'rust',
    'r': 'r'
  };
  if (window.localStorage) {
    $('.ui.search.dropdown.language').dropdown('set selected', localStorage.getItem('lang') || 'cpp');
  }
  var editor = ace.edit("editor");
  var lang = $("#id_lang");
  var code = $("#id_code");
  editor.getSession().setValue(code.val());
  editor.setTheme("ace/theme/chrome");
  editor.getSession().setMode("ace/mode/" + map[lang.val()]);
  editor.setOptions({
    fontFamily: ["Consolas", "Courier", "Courier New", "monospace"],
    fontSize: "11pt"
  });
  lang.on("change", function (event) {
    editor.getSession().setMode("ace/mode/" + map[event.target.value]);
    if (window.localStorage) {
      localStorage.setItem("lang", event.target.value);
    }
  });
  editor.getSession().on("change", function () {
    code.val(editor.getSession().getValue());
  });
}

function scrollToCurrentSubmission () {
  $('html, body').animate({
    scrollTop: $("#current-submission").find("table").offset().top - $("#navbar").height() - 15
  }, 500);
}

function updateSubmission (url, scroll) {
  $.get(url, function (data) {
    var submissionBox = $("#current-submission");
    submissionBox.html(data);
    var status = submissionBox.find(".status-span.with-icon").attr("data-status");
    if (status == "-3" || status == "-2") {
      setTimeout(function() {
        updateSubmission(url, false);
      }, 500);
    } else {
      updatePastSubmissions();
    }
    if (scroll)
      scrollToCurrentSubmission();
    $.parseStatusDisplay();
  });
}

function updatePastSubmissions () {
  var pastSubmissionBox = $("#past-submissions");
  if (pastSubmissionBox.length > 0) {
    $.get(pastSubmissionBox.data("url"), function (data) {
      pastSubmissionBox.html(data);
      $.parseStatusDisplay();
    });
  }
}

$("#problem-submit").click(function (event) {
  var button = $(event.currentTarget);
  var form = button.closest("form");
  form.removeClass("error");
  form.addClass("loading");
  $.post(form.attr("action"), form.serialize())
    .done(function (data) {
      updateSubmission(data.url, true);
      form.removeClass("loading");
    })
    .fail(function (xhr) {
      form.addClass("error");
      if (xhr.hasOwnProperty("responseText") && xhr.responseText) {
        form.find("#error-message-goes-here").html(xhr.responseText);
      } else {
        form.find("#error-message-goes-here").html("Submit failed. Try again later.");
      }
      form.removeClass("loading");
    });
  return false;
});

updatePastSubmissions();