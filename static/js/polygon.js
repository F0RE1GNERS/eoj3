$('.ui.accordion').accordion();
$('#session-create-button').click(function () {
  $("#session-create")
    .modal({
      onApprove : function () {
        $("#session-create-form").submit();
      }
    })
    .modal('show')
  ;
});
$("#session-create-form")
  .form({
    fields: {
      alias: ["regExp[/^[\.a-z0-9_-]{4,64}$/]"]
    }
  })
;
$('.synchronize.button').click(function () {
  $("#session-synchronize-form").find("input[name=problem]").val($(this).data("problem"));
  $("#session-synchronize")
    .modal({
      onApprove: function () {
        $("#session-synchronize-form").submit();
      }
    })
    .modal('show');
});

function clearAndAddExtraData(form, extra_data) {
  form.find('input[type="hidden"][name!="next"][name!="csrfmiddlewaretoken"][data-important!="true"]').remove();
  for (val in extra_data) {
    var already_exist = form.find('input[name="' + val + '"]');
    if (already_exist.length > 0) {
      already_exist.val(extra_data[val]);
    } else {
      form.append("<input type='hidden' name='" + val + "' value='" + extra_data[val] + "'>");
    }
  }
}

function bindFormAndButtonData(form, button) {
  form.attr("action", button.data("action"));
  clearAndAddExtraData(form, button.data());
}

if ($("#session-edit-app").length > 0) {
  // Vue.js needed
  Vue.options.delimiters = ["[[", "]]"];
  new Vue({
    el: "#session-edit-app",
    data: {
      appData: {},
      apiRoute: "",
      errorMessage: "",
      statementEditorData: {
        fileName: "",
        text: "",
        converted: "",
        contentUrl: ""
      }
    },
    watch: {
      statementEditorData: {
        handler: function (newStatement) {
          this.getStatementConverted();
        },
        deep: true
      }
    },
    methods: {
      ping: function () {
        console.log("pong");
      },
      updateConfig: function () {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.appData = data;
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
        if (form.find(".ui.file.input").length > 0) {
          form.find(".ui.file.input").inputFile({
            sizeLimit: this.appData.volume_all - this.appData.volume_used
          });
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
      showStatementEditor: function (event) {
        var button = $(event.currentTarget);
        this.statementEditorData.fileName = button.data("filename");
        var modal = $("#statement-editor");
        var form = modal.find("form");
        bindFormAndButtonData(form, button);
        form.addClass("loading");
        this.statementEditorData.contentUrl = button.data("get-content");
        modal
          .modal({
            onApprove: function () {
              form.submit();
            },
            closable: false
          })
          .modal('show');
        // init editor data
        $.get(this.statementEditorData.contentUrl,
          {"filename": this.statementEditorData.fileName},
          function (data) {
            this.statementEditorData.text = data;
            form.removeClass("loading");
          }.bind(this)
        );
      },
      showUpdateCodeEditor: function (event) {
        var button = $(event.currentTarget);
        $.get(button.data("get-content"), {"filename": button.data("filename")},
          function (data) {
            var local_form = $(button.data("target")).find("form");
            local_form.find("*[name='code']").val(data);
          }.bind(this));
        this.showDialogWithOneForm(event);
      },
      getStatementConverted: _.debounce(
        function () {
          $.post("/api/markdown/", {
            csrfmiddlewaretoken: Cookies.get('csrftoken'),
            text: this.statementEditorData.text
          }, function (data) {
            this.statementEditorData.converted = data;
          }.bind(this))
        },
        1000
      )
    },
    beforeMount: function () {
      this.updateConfig();
    },
    mounted: function () {
      $("#save-meta-form")
        .form({
          fields: {
            alias: ["regExp[/^[a-z0-9_-]{4,64}$/]"],
            time_limit: "integer[200..30000]",
            memory_limit: "integer[64..4096]",
            source: "maxLength[128]"
          }
        });
      $('.tabular.menu .item').tab({
        history: true,
        historyType: 'hash'
      });
      $('.ui.dropdown.onhover').dropdown({
        on: 'hover'
      });
      $('.ui.selection.dropdown').dropdown({
        onChange: function (val) {
          if (val == '(none)')
            $(this).dropdown('clear');
        }
      });
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
              if (data["status"] == "received") {
                target.removeClass("error").addClass("success");
                this.updateConfig();
                this.errorMessage = "";
                setTimeout(function () {
                  target.removeClass("success");
                }, 5000);
              } else {
                target.form('add errors', [data["message"]]);
                this.errorMessage = data["message"];
                target.removeClass("success").addClass("error");
              }
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
    }
  });
}
