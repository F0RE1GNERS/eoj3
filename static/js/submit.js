if (document.getElementById("editor") && window.hasOwnProperty("ace")) {
  // has a editor
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
  const ele = $('.ui.search.dropdown.language');
  const all_lang = ele.find('.item').map(function() { return $(this).data('value'); }).get();
  if (window.localStorage && all_lang.indexOf(localStorage.getItem('lang')) >= 0) {
    ele.dropdown('set selected', localStorage.getItem('lang'));
  } else {
    ele.dropdown('set selected', all_lang[0]);
  }
  var editor = ace.edit("editor");
  var lang = $("#id_lang");
  var code = $("#id_code");
  var problem = $("*[name='problem']");
  var code_param = "", code_in_storage_key = "";
  code.on("change", function (event) {
    editor.getSession().setValue(code.val());
  });

  function updateStorageKey() {
    var problem_val = problem.val();
    if (problem_val) {
      code_param = "?c=" + $("#default-contest").val() + "&p=" + problem_val;
      code_in_storage_key = "code" + code_param;
      if (window.sessionStorage && window.sessionStorage.getItem(code_in_storage_key)) {
        code.val(window.sessionStorage.getItem(code_in_storage_key));
        code.trigger("change");
      } else {
        $.get("/api/submission/" + code_param, function (data) {
          code.val(data);
          code.trigger("change");
        });
      }
    } else {
      code_in_storage_key = "";
    }
  }
  updateStorageKey();

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
  problem.on("change", function (event) {
    updateStorageKey();
  });

  editor.getSession().on("change", function () {
    var my_code = editor.getSession().getValue();
    code.val(my_code);
    if (window.sessionStorage && code_in_storage_key)
      window.sessionStorage.setItem(code_in_storage_key, my_code);
  });
}

function scrollToCurrentSubmission () {
  $('html, body').animate({
    scrollTop: $("#current-submission").offset().top - $("#navbar").height() - 15
  }, 500);
}

var problemUpdateTimeout = null;

function updateSubmission (url, scroll, preset_timeout) {
  $.get(url, function (data) {
    var submissionBox = $("#current-submission");
    submissionBox.html(data);
    var status = submissionBox.find(".status-span.with-icon").attr("data-status");
    if (status == "-3" || status == "-2") {
      problemUpdateTimeout = setTimeout(function() {
        updateSubmission(url, false, (preset_timeout || 500) + 50);
      }, preset_timeout || 500);
    } else {
      updatePastSubmissions();
      updateProblemTags();
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

function updateProblemTags () {
  var fetch_url = location.href.split('?')[0] + "?onlytag=1";
  $.get(fetch_url, function (data) {
    $("#problem-tags").replaceWith(data);
    $('.ui.selection.dropdown.maximum-5')
    .dropdown({
      maxSelections: 5
    });
  });
}

$("#problem-submit").click(function (event) {
  var button = $(event.currentTarget);
  var form = button.closest("form");
  form.removeClass("error");
  form.addClass("loading");
  $.post(form.attr("action"), form.serialize())
    .done(function (data) {
      if (problemUpdateTimeout) clearTimeout(problemUpdateTimeout);
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