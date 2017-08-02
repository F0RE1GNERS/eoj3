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

// status string
window.STATUS = {};
window.STATUS[-4] = 'Submitted';
window.STATUS[-3] = 'Waiting';
window.STATUS[-2] = 'Judging';
window.STATUS[-1] = 'Wrong Answer';
window.STATUS[0] = 'Accepted';
window.STATUS[1] = 'Time Limit Exceeded';
window.STATUS[2] = 'Idleness Limit Exceeded';
window.STATUS[3] = 'Memory Limit Exceeded';
window.STATUS[4] = 'Runtime Error';
window.STATUS[5] = 'System Error';
window.STATUS[6] = 'Compile Error';
window.STATUS[7] = 'Idleness Limit Exceeded';
window.STATUS[8] = 'Time Limit Exceeded';
window.STATUS[11] = 'Judge Error';
window.STATUS[12] = 'Pretest Passed';

window.STATUS_COLOR = {};
window.STATUS_COLOR[-4] = 'black';
window.STATUS_COLOR[-3] = 'blue';
window.STATUS_COLOR[-2] = 'blue';
window.STATUS_COLOR[-1] = 'red';
window.STATUS_COLOR[0] = 'green';
window.STATUS_COLOR[1] = 'orange';
window.STATUS_COLOR[2] = 'orange';
window.STATUS_COLOR[3] = 'orange';
window.STATUS_COLOR[4] = 'yellow';
window.STATUS_COLOR[5] = 'yellow';
window.STATUS_COLOR[6] = 'grey';
window.STATUS_COLOR[7] = 'orange';
window.STATUS_COLOR[8] = 'orange';
window.STATUS_COLOR[11] = 'orange';
window.STATUS_COLOR[12] = 'green';
