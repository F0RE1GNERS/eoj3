if (document.getElementById("editor") && window.hasOwnProperty("ace")) {
  // has a editor
  var map = {
    'c': {
      'mode': 'c_cpp', 'name': 'C'
    },
    'cpp': {
      'mode': 'c_cpp', 'name': 'C++11'
    },
    'python': {
      'mode': 'python', 'name': 'Python 3'
    },
    'java': {
      'mode': 'java', 'name': 'Java 8'
    },
    'cc14': {
      'mode': 'c_cpp', 'name': 'C++14'
    },
    'cc17': {
      'mode': 'c_cpp', 'name': 'C++17'
    },
    'cs': {
      'mode': 'csharp', 'name': 'C#'
    },
    'py2': {
      'mode': 'python', 'name': 'Python 2'
    },
    'scipy': {
      'mode': 'python', 'name': 'Python (SCI)'
    },
    'php': {
      'mode': 'php', 'name': 'PHP 7'
    },
    'perl': {
      'mode': 'perl', 'name': 'Perl'
    },
    'hs': {
      'mode': 'haskell', 'name': 'Haskell'
    },
    'js': {
      'mode': 'javascript', 'name': 'JavaScript'
    },
    'ocaml': {
      'mode': 'ocaml', 'name': 'OCaml'
    },
    'pypy': {
      'mode': 'python', 'name': 'PyPy'
    },
    'pypy3': {
      'mode': 'python', 'name': 'PyPy 3'
    },
    'pas': {
      'mode': 'pascal', 'name': 'Pascal'
    },
    'rs': {
      'mode': 'rust', 'name': 'Rust'
    },
    'scala': {
      'mode': 'scala', 'name': 'Scala'
    },
    'text': {
      'mode': 'text', 'name': 'Text'
    },
    'auto': {
      'mode': 'c_cpp', 'name': 'Detecting'
    }
  };
  var lang_key = "lang?c=" + $("#default-contest").val();
  var ele = $('.ui.search.dropdown.language');
  var all_lang = ele.find('.item').map(function () {
    return $(this).data('value');
  }).get();
  if (window.localStorage && all_lang.indexOf(localStorage.getItem(lang_key)) >= 0) {
    ele.dropdown('set selected', localStorage.getItem(lang_key));
  } else {
    ele.dropdown('set selected', 'auto');
  }
  var editor = ace.edit("editor");
  var lang = $("#id_lang");
  var code = $("#id_code");
  var problem = $("*[name='problem']");
  var code_param = "", code_in_storage_key = "";
  var auto_lang = ele.dropdown('get value') == "auto";
  var detected_lang = "cpp";
  var template_button = $("#template-button");

  function detectLanguage() {
    detected_lang = detectLang(code.val(), all_lang);
    $('.detected-lang-name').text(map[detected_lang].name);
    if (auto_lang) {
      if (lang.val() != detected_lang) {
        lang.val(detected_lang);
        editor.getSession().setMode("ace/mode/" + map[detected_lang].mode);
      }
    }
  }
  var detectLanguageDebouncer = _.debounce(detectLanguage, 100);

  code.on("change", function (event) {
    editor.getSession().setValue(code.val());
    detectLanguageDebouncer();
  });

  function updateWithTemplate() {
    var selector = $("#code_template_" + lang.val());
    if (selector.length > 0) {
      template_button.show();
      code.val(selector.html());
      code.trigger("change");
    } else {
      template_button.hide();
    }
  }

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
      if (!code.val()) updateWithTemplate();
    } else {
      code_in_storage_key = "";
    }
  }

  updateWithTemplate();
  updateStorageKey();
  detectLanguage();

  editor.setTheme("ace/theme/chrome");
  editor.getSession().setMode("ace/mode/" + map[auto_lang ? detected_lang : lang.val()].mode);
  editor.setOptions({
    fontFamily: ["Consolas", "Courier", "Courier New", "monospace"],
    fontSize: "11pt"
  });

  var ignore_change = false;

  lang.on("change", function (event) {
    if (ignore_change) {
      ignore_change = false;
      return;
    }
    detectLanguage();
    auto_lang = event.target.value == "auto";
    if (auto_lang) {
      ignore_change = true;
      lang.val(detected_lang);
    }
    editor.getSession().setMode("ace/mode/" + map[event.target.value].mode);
    if (window.localStorage) {
      localStorage.setItem(lang_key, auto_lang ? "auto" : event.target.value);
    }
    updateWithTemplate();
  });
  problem.on("change", function (event) {
    updateStorageKey();
  });

  editor.getSession().on("change", function () {
    var my_code = editor.getSession().getValue();
    code.val(my_code);
    detectLanguageDebouncer();
    if (window.sessionStorage && code_in_storage_key)
      window.sessionStorage.setItem(code_in_storage_key, my_code);
  });

  // paste listener
  document.addEventListener('paste', function (e) {
    var clipboard = e.clipboardData;
    if (!clipboard.items || !clipboard.items.length || $(e.target).attr('class') === "ace_text-input") {
      detectLanguage(true);
      return;
    }
    var item = clipboard.items[0];
    if (item.kind === "string") {
      item.getAsString(function (str) {
        editor.getSession().setValue(str);
      });
      $('html, body').animate({
        scrollTop: $("#submit-form").offset().top - $("#navbar").height() - 15
      }, 500);
      detectLanguage(true);
    }
  }, false);

  template_button.on('click', updateWithTemplate);
}

function scrollToCurrentSubmission() {
  $('html, body').animate({
    scrollTop: $("#current-submission").offset().top - $("#navbar").height() - 15
  }, 500);
}

var problemUpdateTimeout = null;

function updateSubmission(url, scroll, preset_timeout) {
  $.get(url, function (data) {
    var submissionBox = $("#current-submission");
    submissionBox.html(data);
    var status = submissionBox.find(".status-span.with-icon").attr("data-status");
    if (status == "-3" || status == "-2") {
      problemUpdateTimeout = setTimeout(function () {
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

function updatePastSubmissions() {
  var pastSubmissionBox = $("#past-submissions");
  if (pastSubmissionBox.length > 0) {
    $.get(pastSubmissionBox.data("url"), function (data) {
      pastSubmissionBox.html(data);
      $.parseStatusDisplay();
    });
  }
}

function updateProblemTags() {
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
  detectLanguage();
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

$("a[href='#top']").click(function () {
  $("html, body").animate({scrollTop: 0}, "slow");
  return false;
});