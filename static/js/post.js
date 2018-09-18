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
    console.log(extra_input["answer"] !== null);
    if (extra_input["answer"] !== null)
      redirect(link, method, extra_input);
  } else if (button.hasClass("prompt")) {
    if (confirm("Are you sure about this?"))
      redirect(link, method, extra_input);
  } else {
    redirect(link, method, extra_input);
  }
}).attr('href', 'javascript:void(0)');