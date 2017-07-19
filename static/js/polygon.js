$("#save-meta-form")
  .form({
    fields: {
      alias: ["regExp[/^[a-z0-9_-]{4,64}$/]"],
      time_limit: "integer[200..30000]",
      memory_limit: "integer[64..4096]",
      source: "maxLength[128]"
    }
  });

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
$('.tabular.menu .item').tab();