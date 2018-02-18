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

function redirect(url, method) {
  var form = document.createElement('form');
  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'csrfmiddlewaretoken';
  input.value = Cookies.get('csrftoken');
  form.appendChild(input);
  document.body.appendChild(form);
  form.method = method;
  form.action = url;
  form.submit();
}

$(".post").on('click', function (event) {
  var button = $(event.currentTarget);
  var link = button.data("link");
  if (button.hasClass("prompt")) {
    if (confirm("Are you sure about this?"))
      redirect(link, "post");
  } else {
    redirect(link, "post");
  }
});

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