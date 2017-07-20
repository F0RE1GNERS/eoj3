$('.ui.accordion').accordion();
$('#session-create-button').click(function() {
  $("#session-create")
    .modal({
      onApprove : function() {
        $("#session-create-form").submit();
      }
    })
    .modal('show')
  ;
});
$("#session-create-form")
  .form({
    fields: {
      alias: ["regExp[/^[a-z0-9_-]{4,64}$/]"]
    }
  })
;
$('.synchronize.button').click(function() {
  $("#session-synchronize-form").find("input[name=problem]").val($(this).data("problem"));
  $("#session-synchronize")
    .modal({
      onApprove: function() {
        $("#session-synchronize-form").submit();
      }
    })
    .modal('show');
});

if ($("#session-edit-app").length > 0) {
  // Vue.js needed
  Vue.options.delimiters = ["[[", "]]"];
  new Vue({
    el: "#session-edit-app",
    data: {
      appData: {},
      apiRoute: "",
      errorMessage: ""
    },
    methods: {
      updateConfig: function() {
        this.apiRoute = $(this.$el).data("api-route");
        $.getJSON(this.apiRoute, function (data) {
          this.appData = data;
        }.bind(this));
      }
    },
    beforeMount: function() {
      this.updateConfig();
    },
    mounted: function() {
      $("#save-meta-form")
        .form({
          fields: {
            alias: ["regExp[/^[a-z0-9_-]{4,64}$/]"],
            // time_limit: "integer[200..30000]",
            // memory_limit: "integer[64..4096]",
            source: "maxLength[128]"
          }
        });
      $('.tabular.menu .item').tab({
        history: true,
        historyType: 'hash'
      });
      $('form').submit(function (event) {
        var target = $(event.target);
        if (target.form('is valid')) {
          $.post(target.prop("action"), target.serialize(), function (data) {
            if (data["status"] == "received") {
              target.removeClass("error").addClass("success");
              this.updateConfig();
              setTimeout(function () {
                target.removeClass("success");
              }, 5000);
            } else {
              target.form('add errors', [data["message"]]);
              this.errorMessage = data["message"];
              target.removeClass("success").addClass("error");
            }
          }.bind(this), "json");
          return false;
        }
      }.bind(this));

      $('.ui.button.delete').click(function() {
        $("#delete-confirmation-form").prop("action", $(this).data("action"));
        $("#delete-confirmation")
          .modal({
            onApprove: function() {
              $("#delete-confirmation-form").submit();
            }
          })
          .modal('show');
      });

      $('*[data-description="open-a-modal-with-one-form"]').click(function() {
        var local_modal = $($(this).data("target"));
        local_modal
          .modal({
            onApprove : function() {
              $(this).find("form").submit();
            }.bind(local_modal[0])
          })
          .modal('show')
        ;
      })
    }
  });
}

