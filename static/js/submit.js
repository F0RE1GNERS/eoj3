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
  fontSize: "12pt"
});
lang.on("change", function (event) {
  editor.getSession().setMode("ace/mode/" + map[event.target.value]);
});
editor.getSession().on("change", function () {
  code.val(editor.getSession().getValue());
});

$("#problem-submit").click(function (event) {
  var button = $(event.currentTarget);
  var form = button.closest("form");
  form.addClass("loading");
  $.post(form.attr("action"), form.serialize(), function () {
    vm.updateSubmission();
    form.removeClass("loading");
    $('html, body').animate({
      scrollTop: $("#older-submission").offset().top - $("#navbar").height() - 15
    }, 500);
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
      subcurrent: {},
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
        if (this.current < 0 || this.current >= this.submission.length) {
          this.time = 'NaN';
        } else {
          this.subcurrent = this.submission[this.current];
          if (typeof this.submission[this.current].status_time == 'number')
            this.time = this.submission[this.current].status_time.toFixed(3) + 's';
          else this.time = 'NaN';
          console.log(this.subcurrent);
          for (var i = 0; i < this.subcurrent.status_detail_list.length; ++i) {
            if (!this.subcurrent.status_detail_list[i].hasOwnProperty("verdict"))
              this.subcurrent.status_detail_list[i].verdict = -3;
          }
        }
      },
      updateSubmission: function () {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.submission = data;
          var toUpdate = -1;
          for (var i = 0; i < this.submission.length; ++i) {
            if (this.submission[i].status == -2 || this.submission[i].status == -3) {
              toUpdate = i;
              break;
            }
          }
          if (toUpdate >= 0) {
            this.current = toUpdate;
            setTimeout(function () {
              this.updateSubmission();
            }.bind(this), 500);
          }
          this.updateCurrentDisplay();
        }.bind(this));
      },
      toggleCurrent: function (event) {
        this.current = $(event.currentTarget).attr("index");
        $('html, body').animate({
          scrollTop: $("#older-submission").offset().top - $("#navbar").height() - 15
        }, 500);
      }
    },
    beforeMount: function () {
      this.updateSubmission();
    },
    mounted: function () {
      new Clipboard('.clipboard');
    }
  });
}
