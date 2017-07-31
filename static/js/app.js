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


$('.ui.dropdown.user-search')
  .dropdown({
    apiSettings: {
      url: '/api/search/user/?kw={query}'
    }
  })
;