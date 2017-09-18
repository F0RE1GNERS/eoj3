$('.ui.accordion').accordion();
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
$('.run-message-reveal-link').click(function (event) {
  $.get($(event.currentTarget).data("get-action"), {}, function (data) {
    if (!data) data = '[ This message is empty. ]';
    var modal = $("#message-preview-modal");
    modal.find("code").html(data);
    modal.modal('show');
  });
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

function clearAndAddExtraData(form, extra_data) {
  form.find('input[type="hidden"][name!="next"][name!="csrfmiddlewaretoken"][data-important!="true"]').remove();
  for (var val in extra_data) {
    if (extra_data.hasOwnProperty(val)) {
      var already_exist = form.find('input[name="' + val + '"]');
      if (already_exist.length > 0) {
        already_exist.val(extra_data[val]);
      } else {
        form.append("<input type='hidden' name='" + val + "' value='" + extra_data[val] + "'>");
      }
    }
  }
}

function bindFormAndButtonData(form, button) {
  button.removeData();
  form.attr("action", button.data("action"));
  clearAndAddExtraData(form, button.data());
}

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
      }
    },
    methods: {
      ping: function () {
        console.log("pong");
      },
      updateConfig: function () {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.caseList = data;
          console.log(this.caseList);
          for (var i = 0; i < this.caseList.length; ++i)
            this.caseList[i].used = this.caseList[i].order > 0;
        }.bind(this));
      },
      clearErrorMessage: function () {
        this.errorMessage = "";
      },
      showDeleteDialog: function (event) {
        bindFormAndButtonData($("#delete-confirmation-form"), $(event.currentTarget));
        $("#delete-confirmation")
          .modal({
            onApprove: function () {
              $("#delete-confirmation-form").submit();
            }
          })
          .modal('show');
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
      saveCaseOrders: function (event) {
        $.post($(event.currentTarget).data("action"), {
          'case': JSON.stringify(this.caseList),
          'unused': JSON.stringify(this.unusedCaseList),
          'csrfmiddlewaretoken': Cookies.get('csrftoken')
        }, function (data) {
          $("#success-modal").modal('show');
          this.updateConfig();
        }.bind(this),
        "json");
      },
      convertStatusCodeToHelpText: function (statusCode) {
        if (statusCode == 1) {
          return "Yes";
        } else if (statusCode == -1) {
          return "No";
        } else {
          return "Unknown";
        }
      },
      previewCase: function (event) {
        var button = $(event.currentTarget);
        $.get(button.data("get-action"), {
          'case': button.data("fingerprint")
        }, function (data) {
          this.previewCaseInput = data.input;
          this.previewCaseOutput = data.output;
        }.bind(this), "json");
        $("#case-preview-modal").modal('show');
      }
    },
    beforeMount: function () {
      this.updateConfig();
    },
    mounted: function () {
      $('.tabular.menu .item').tab({
        history: true,
        historyType: 'hash'
      });
      $('.ui.dropdown.onhover').dropdown({
        on: 'hover'
      });
      $('.ui.checkbox').checkbox();
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
            success: function (data) {
              this.updateConfig();
            }.bind(this),
            complete: function () {
              if (progressBar) {
                setTimeout(function () {
                  progressBar.hide();
                }, 2000);
              }
            },
            cache: false,
            contentType: false,
            processData: false,
            dataType: "json",
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
      $('.ui.checkbox').checkbox();
      $('.ui.selection.dropdown').dropdown();
    }
  });
}

if ($("#contest-edit-app").length > 0) {
  Vue.options.delimiters = ["[[", "]]"];
  new Vue({
    el: "#contest-edit-app",
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
        }.bind(this), "json");
      },
      reorderProblem: function () {
        var data = { 'orders': JSON.stringify(this.appData) };
        data = this.addCsrfToken(data);
        $.post($(event.currentTarget).data("url"), data, function (data) {
          this.updateConfig();
        }.bind(this), "json");
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
            }.bind(this), "json");
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