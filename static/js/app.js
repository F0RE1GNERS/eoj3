// ui
$('.ui.checkbox')
  .checkbox()
;
$('.message .close')
  .on('click', function() {
    $(this)
      .closest('.message')
      .transition('fade')
    ;
  })
;

// captcha
$('.captcha-refresh, img.captcha').click(function(){
  var $form = $(this).parents('form');
  $.getJSON("/captcha/refresh/", {}, function(json) {
    $form.find('input[name="captcha_0"]').val(json.key);
    $form.find('img.captcha').attr('src', json.image_url);
  });
  return false;
});

// navbar search
$('.ui.search.massive-search').search({
  type: 'category',
  apiSettings: {
    url: '/api/search/?kw={query}'
  },
  minCharacters: 1
});
$('.ui.search.dropdown.language')
  .dropdown();
$('.ui.dropdown.user-search')
  .dropdown({
    apiSettings: {
      url: '/api/search/user/?kw={query}'
    }
  })
;

$(".post-link")
  .on('click', function(e) {
    var link = $(e.currentTarget).data('link');
    $.post(link, {'csrfmiddlewaretoken': Cookies.get('csrftoken')}, function (data) {
        location.reload();
      }
    );
  })
  .attr('href', 'javascript:void(0)');

$(".delete-link")
  .on('click', function (e) {
    var link = $(e.currentTarget).data('link');
    $("#delete-confirmation")
      .modal({
        onApprove: function () {
          $.post(link, {'csrfmiddlewaretoken': Cookies.get('csrftoken')}, function (data) {
              location.reload();
            }
          );
        }
      })
      .modal('show');
  })
  .attr('href', 'javascript:void(0)');

$(".ui.checkbox.immediate")
  .checkbox({
    onChange: function () {
      var link = $(this).data('link');
      $.post(link, {
        'csrfmiddlewaretoken': Cookies.get('csrftoken'),
        'checked': $(this).prop('checked')
      }, function (data) {
        location.reload();
      });

    }
  });