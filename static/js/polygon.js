$('.ui.accordion').accordion();
$('.ui.pointing.dropdown.button').dropdown();
$('.ui.calendar').calendar({
  formatter: {
    date: function (date, settings) {
      return moment(date).format('YYYY-MM-DD');
    },
    time: function (date, settings, forCalendar) {
      return moment(date).format('HH:mm');
    }
  }
});

$('#contest-create-button').click(function () {
  $("#contest-create")
    .modal('show');
});
$("#session-create-form")
  .form({
    fields: {
      alias: ["regExp[/^[\.a-z0-9_-]{4,64}$/]"]
    }
  })
;
$(".loader-button").click(function () {
  $("#loading-dimmer").addClass("active");
  return true;
});

function updateRunNumber(delta) {
  var run_number_label = $("#run-number"),
    new_number = parseInt(run_number_label.html()) + delta;
  run_number_label.html(new_number);
  if (new_number > 0)
    run_number_label.removeClass("hidden");
  else
    run_number_label.addClass("hidden");
}

function bindFormAndButtonData(form, button) {
  button.removeData();
  form.attr("action", button.data("action"));
  replaceFormData(form, button.data());
}

function redirect(url, method, extra_input) {
  var form = document.createElement('form');
  extra_input["csrfmiddlewaretoken"] = Cookies.get('csrftoken');  // add csrf token
  for (var key in extra_input)
    if (extra_input.hasOwnProperty(key)) {
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = key;
      input.value = extra_input[key];
      form.appendChild(input);
    }
  document.body.appendChild(form);
  form.method = method;
  form.action = url;
  form.submit();
}

$("input[name='all']").on('change', function() {
  $("input[type='checkbox']").prop('checked', this.checked);
});

var lastChecked = null;
var slicedCheckbox = $(".ui.checkbox.slice");
slicedCheckbox.on('click', function (e) {
  // check all checked
  var allChecked = true;
  for (var i = 0; i < slicedCheckbox.length; ++i) {
    if (!($(slicedCheckbox[i]).checkbox("is checked"))) {
      allChecked = false;
      break;
    }
  }
  $("input[name='all']").prop('checked', allChecked);
  if (!lastChecked) {
    lastChecked = this;
    return;
  }
  if (e.shiftKey) {
    var start = slicedCheckbox.index(this);
    var end = slicedCheckbox.index(lastChecked);
    slicedCheckbox.slice(Math.min(start, end), Math.max(start, end) + 1)
      .checkbox($(lastChecked).checkbox("is checked") ? "check" : "uncheck");
  }
  lastChecked = this;
});

$(".post, .get").on('click', function (event) {
  var button = $(event.currentTarget);
  var method = button.hasClass("post") ? "post" : "get";
  var link = button.data("link");
  var extra_input = {};
  if (button.hasClass("gather")) {
    // gather all checkbox information
    extra_input["gather"] = $.makeArray($("input[type='checkbox']").map(function() {
      return this.checked ? this.name : "";
    })).filter(function(n) {
      return n != "all" && n != "";
    }).join(",");
    if (!extra_input["gather"]) {
      alert("Please select cases first!");
      return;
    }
  }
  if (button.hasClass("ask")) {
    extra_input["answer"] = prompt(button.data("question") || "");
    if (extra_input["answer"] !== null)
      redirect(link, method, extra_input);
  } if (button.hasClass("prompt")) {
    if (confirm("Are you sure about this?"))
      redirect(link, method, extra_input);
  } else {
    redirect(link, method, extra_input);
  }
}).attr('href', 'javascript:void(0)');

if ($("#session-case-app").length > 0) {
  // Vue.js needed
  Vue.options.delimiters = ["[[", "]]"];
  new Vue({
    el: "#session-case-app",
    data: {
      apiRoute: "",
      errorMessage: "",
      caseList: [],
      previewCaseInput: "",
      previewCaseOutput: "",
      generateParam: ""
    },
    computed: {
      generateParamLength: function () {
        return this.generateParam.split('\n').length;
      },
      selectedId: function () {
        return this.caseList.filter(function (c) {
          return c.selected;
        }).map(function (c) {
          return c.fingerprint;
        }).join(',');
      }
    },
    methods: {
      ping: function () {
        console.log("pong");
      },
      updateConfig: function () {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.caseList = data['caseList'];
          for (var i = 0; i < this.caseList.length; ++i)
            this.caseList[i].used = this.caseList[i].order > 0;
        }.bind(this));
      },
      clearErrorMessage: function () {
        this.errorMessage = "";
      },
      showDeleteDialog: function (event) {
        button = $(event.currentTarget);
        $("#delete-confirmation")
          .modal({
            onApprove: function () {
              $.post(button.attr("data-action"), {
                csrfmiddlewaretoken: Cookies.get('csrftoken'),
                id: button.attr("data-id")
              }, function () {
                this.updateConfig();
              }.bind(this));
            }.bind(this)
          })
          .modal('show');
      },
      initializeCaseEditor: function (event) {
        var url = $(event.currentTarget).attr("data-api");
        var modal = $("#case-edit-modal");
        $.getJSON(url, function (data) {
          var inputText = modal.find("*[name='inputText']"),
            outputText = modal.find("*[name='outputText']"),
            fileInput = modal.find(".file.input"),
            pointInput = modal.find("*[name='point']"),
            sampleCheckbox = modal.find("*[name='sample']"),
            pretestCheckbox = modal.find("*[name='pretest']"),
            formatCheckbox = modal.find("*[name='reform']");
          fileInput.find("input").val('');
          modal.find(".ui.file.input").inputFile();
          inputText.prop("readonly", data.input.nan);
          inputText.val(data.input.text);
          outputText.prop("readonly", data.output.nan);
          outputText.val(data.output.text);
          pointInput.val(data.point);
          sampleCheckbox.prop("checked", data.sample);
          pretestCheckbox.prop("checked", data.pretest);
          formatCheckbox.prop("checked", true);
          modal.modal({
            closable: false,
            autofocus: false,
            onApprove: function () {
              modal.find("form").attr("action", url);
              modal.find("form").submit();
            }
          }).modal('show');
        }.bind(this));
      },
      showDialogWithOneForm: function (event) {
        var button = $(event.currentTarget);
        var local_modal = $(button.data("target"));
        var form = local_modal.find("form");
        bindFormAndButtonData(form, button);
        var autofocus = true, closable = true;
        if (button.data("block"))
          closable = false;
        if (form.find(".ui.dropdown", "select").length > 0) {
          form.find(".ui.dropdown").dropdown();
          autofocus = false;
        }
        if (form.find(".ui.checkbox").length > 0) {
          form.find(".ui.checkbox").checkbox();
        }
        if (form.find(".ui.file.input").length > 0) {
          form.find(".ui.file.input").inputFile();
          autofocus = false;
        }
        local_modal
          .modal({
            autofocus: autofocus,
            closable: closable,
            onApprove : function () {
              form.submit();
            }
          })
          .modal('show');
      },
      postLink: function (event) {
        var data = { csrfmiddlewaretoken: Cookies.get('csrftoken') };
        var buttonData = $(event.currentTarget).data();
        $.post(buttonData['action'], Object.assign(data, buttonData), function (data) {
          this.updateConfig();
        }.bind(this))
      },
      showTargetModalNaive: function (event) {
        $($(event.currentTarget).data("target")).modal('show');
      },
      saveChanges: function (event) {
        $.post($(event.currentTarget).data("url"), {
          'case': JSON.stringify(this.caseList),
          'csrfmiddlewaretoken': Cookies.get('csrftoken')
        }, function () {
          $("#success-modal").modal('show');
          this.updateConfig();
        }.bind(this));
      },
      toggleSelectAll: function () {
        var ans = true;
        if (this.caseList.every(function (element) {
          return element.selected;
        })) {
          ans = false;
        }
        for (var i = 0; i < this.caseList.length; ++i)
          this.caseList[i].selected = ans;
      }
    },
    beforeMount: function () {
      this.updateConfig();
    },
    mounted: function () {
      $('.tabular.menu .item').tab({
        history: false,
        onLoad: function () {
          $(this).siblings("input[type='hidden']").val($(this).attr("data-type"));
        }
      });
      $('.ui.dropdown.onhover').dropdown({
        on: 'hover'
      });
      $('.ui.checkbox:not(.vue)').checkbox();
      $('.ui.selection.dropdown').dropdown();
      $(".ui.icon.pointing.dropdown.button")
        .dropdown();
      new Clipboard('.clipboard');
      $('form').submit(function (event) {
        var target = $(event.target);
        var progressBar = target.data("progress-bar") ? $(target.data("progress-bar")) : null;
        if (target.form('is valid')) {
          var formData = new FormData(target[0]);
          $.ajax({
            url: target.attr("action"),
            type: 'POST',
            data: formData,
            success: function () {
              this.updateConfig();
            }.bind(this),
            complete: function (data) {
              if (progressBar) {
                setTimeout(function () {
                  progressBar.hide();
                }, 2000);
              }
            },
            cache: false,
            contentType: false,
            processData: false,
            xhr: function () {
              var myXhr = $.ajaxSettings.xhr();
              if (myXhr.upload && progressBar) {
                // For handling the progress of the upload
                progressBar.show();
                progressBar.progress();
                myXhr.upload.addEventListener('progress', function(e) {
                  if (e.lengthComputable) {
                    progressBar.progress('set total', e.total);
                    progressBar.progress('set progress', e.loaded);
                  }
                } , false);
              }
              return myXhr;
            }
          });
          return false;
        }
      }.bind(this));
    },
    updated: function () {
      $(".ui.icon.pointing.dropdown.button")
        .dropdown();
      $('.ui.selection.dropdown').dropdown();
    }
  });
}

if ($("#contest-problem-app").length > 0) {
  Vue.options.delimiters = ["[[", "]]"];
  new Vue({
    el: "#contest-problem-app",
    data: {
      appData: []
    },
    methods: {
      updateConfig: function () {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.appData = data;
        }.bind(this));
      },
      addCsrfToken: function (data) {
        data['csrfmiddlewaretoken'] = Cookies.get('csrftoken');
        return data;
      },
      addProblem: function () {
        var data = { 'problems': $("#add_problem_input").val() };
        data = this.addCsrfToken(data);
        $.post($(event.currentTarget).data("url"), data, function (data) {
          this.updateConfig();
        }.bind(this));
      },
      reorderProblem: function () {
        var data = { 'orders': JSON.stringify(this.appData) };
        data = this.addCsrfToken(data);
        $.post($(event.currentTarget).data("url"), data, function (data) {
          this.updateConfig();
        }.bind(this));
      },
      readjustProblemPoint: function (e) {
        var modal = $("#problem-point-modal");
        var form = modal.find("form");
        var problem = $(e.currentTarget).data("id");
        modal.modal({
          onApprove: function () {
            $.post(form.attr("action"), this.addCsrfToken({
              'pid': problem,
              'weight': form.find("input[name='weight']").val()
            }), function (data) {
              this.updateConfig();
            }.bind(this));
          }.bind(this)
        }).modal('show');
      },
      readjustProblemIdentifier: function (e) {
        var modal = $("#problem-identifier-modal");
        var form = modal.find("form");
        var problem = $(e.currentTarget).data("id");
        modal.modal({
          onApprove: function () {
            $.post(form.attr("action"), this.addCsrfToken({
              'pid': problem,
              'identifier': form.find("input[name='identifier']").val()
            }), function (data) {
              this.updateConfig();
            }.bind(this));
          }.bind(this)
        }).modal('show');
      },
      deleteConfirmation: function (e) {
        var button = $(e.currentTarget);
        $("#delete-confirmation")
          .modal({
            onApprove: function () {
              $.post(button.data("url"), {
                'csrfmiddlewaretoken': Cookies.get('csrftoken'),
                'pid': button.data("pid")
              }, function (data) {
                this.updateConfig();
              }.bind(this));
            }.bind(this)
          })
          .modal('show');
      }
    },
    beforeMount: function () {
      this.updateConfig();
    },
    mounted: function () {
      $('.ui.dropdown.problem-search')
        .dropdown({
          apiSettings: {
            url: $(this).data('query') || '/api/search/problem/?kw={query}'
          }
        });
    }
  });
}