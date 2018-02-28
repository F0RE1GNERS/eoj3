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
console.log(slicedCheckbox);
slicedCheckbox.on('click', function (e) {
  console.log(lastChecked);
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

$(".post").on('click', function (event) {
  var button = $(event.currentTarget);
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
    redirect(link, "post", extra_input);
  } if (button.hasClass("prompt")) {
    if (confirm("Are you sure about this?"))
      redirect(link, "post", extra_input);
  } else {
    redirect(link, "post", extra_input);
  }
}).attr('href', 'javascript:void(0)');

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