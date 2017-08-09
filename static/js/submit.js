var map = {
  'c': 'c_cpp',
  'c11': 'c_cpp',
  'cpp98': 'c_cpp',
  'cpp': 'c_cpp',
  'cpp14': 'c_cpp',
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
var editor = ace.edit("editor");
var lang = $("#id_lang");
var code = $("#id_code");
editor.getSession().setValue(code.val());
editor.setTheme("ace/theme/chrome");
editor.getSession().setMode("ace/mode/" + map[lang.val()]);
editor.setOptions({
  fontFamily: "Courier",
  fontSize: "11pt"
});
lang.on("change", function (event) {
  editor.getSession().setMode("ace/mode/" + map[event.target.value]);
});
editor.getSession().on("change", function () {
  code.val(editor.getSession().getValue());
});

function scrollToCurrentSubmission () {
  $('html, body').animate({
    scrollTop: $("#older-submission").offset().top - $("#navbar").height() - 15
  }, 500);
}

$("#problem-submit").click(function (event) {
  var button = $(event.currentTarget);
  var form = button.closest("form");
  form.addClass("loading");
  $.post(form.attr("action"), form.serialize(), function () {
    vm.updateSubmission(true);
    form.removeClass("loading");
    scrollToCurrentSubmission();
  });
  return false;
});

if ($("#older-submission").length > 0) {
  Vue.options.delimiters = ["[[", "]]"];
  window.vm = new Vue({
    el: "#older-submission",
    data: {
      submission: [],
      current: -1,
      time: 'NaN',
      subcurrent: "",
      LANGUAGE_DISPLAY: window.LANGUAGE_DISPLAY,
      STATUS_COLOR: window.STATUS_COLOR,
      STATUS_ICON: window.STATUS_ICON,
      STATUS: window.STATUS
    },
    watch: {
      current: {
        handler: function (newStatement) {
          this.updateCurrentDisplay();
        }
      }
    },
    methods: {
      updateCurrentDisplay: function () {
        var c = this.current;
        if (c >= 0 && c < this.submission.length) {
          $.get('/submission/rendered/' + this.submission[c].id, function (data) {
            this.subcurrent = data;
          }.bind(this));
        } else {
          this.subcurrent = "";
        }
      },
      updateSubmission: function (resetCurrent) {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.submission = data;
          if (resetCurrent) {
            this.current = 0;
          }
          if (this.submission[this.current].status == -2 || this.submission[this.current].status == -3) {
            setTimeout(function () {
              this.updateSubmission();
            }.bind(this), 500);
          }
          this.updateCurrentDisplay();
        }.bind(this));
      },
      toggleCurrent: function (event) {
        this.current = $(event.currentTarget).attr("index");
        scrollToCurrentSubmission();
        this.updateSubmission();
      }
    },
    beforeMount: function () {
      this.updateSubmission();
    },
    mounted: function () {
      new Clipboard('.clipboard');
    },
    updated: function () {
      $.parseStatusDisplay();
    }
  });
}
