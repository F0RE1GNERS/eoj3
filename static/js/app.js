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

// url param plugin
function getUrlParamAsObject () {
  var search = location.search.substring(1);
  return search ? JSON.parse('{"' + search.replace(/&/g, '","').replace(/=/g,'":"') + '"}',
                             function (key, value) { return key === "" ? value : decodeURIComponent(value) })
                : {};
}
function encodeObjectAsUrlParamString (myObject) {
  return '?' + $.param(myObject);
}

$('.ui.accordion.status-filter').accordion({
  onClose: function () {
    $(this).find('.ui.dropdown')
      .dropdown('clear');
  }
});
$('.ui.dropdown.status-filter').each(function () {
  var api_url = null;
  if ($(this).data('filter-type') == 'user')
    api_url = '/api/search/user/?kw={query}';
  else if ($(this).data('filter-type') == 'problem')
    api_url = '/api/search/problem/?kw={query}';
  $(this).dropdown({
    onChange: function (value) {
      var obj = getUrlParamAsObject();
      var type = $(this).data('filter-type');
      if (value == 'all')
        value = '';
      if (!value && obj.hasOwnProperty(type)) {
        delete obj[type];
      } if (value) {
        obj[type] = value;
      }
      console.log(obj);
      location.href = encodeObjectAsUrlParamString(obj);
    }.bind(this),
    apiSettings: api_url ? {
      url: api_url
    } : false
  });
});

$('.ui.dropdown.user-search')
  .dropdown({
    apiSettings: {
      url: $(this).data('query') || '/api/search/user/?kw={query}'
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
window.STATUS_COLOR[-233] = '';
window.STATUS_COLOR[-4] = 'black';
window.STATUS_COLOR[-3] = 'blue';
window.STATUS_COLOR[-2] = 'blue';
window.STATUS_COLOR[-1] = 'red';
window.STATUS_COLOR[0] = 'green';
window.STATUS_COLOR[1] = 'orange';
window.STATUS_COLOR[2] = 'orange';
window.STATUS_COLOR[3] = 'orange';
window.STATUS_COLOR[4] = 'yellow';
window.STATUS_COLOR[5] = 'violet';
window.STATUS_COLOR[6] = 'grey';
window.STATUS_COLOR[7] = 'orange';
window.STATUS_COLOR[8] = 'orange';
window.STATUS_COLOR[11] = 'orange';
window.STATUS_COLOR[12] = 'green';

window.STATUS_ICON = {};
window.STATUS_ICON[-233] = '';
window.STATUS_ICON[-4] = 'help';
window.STATUS_ICON[-3] = 'help';
window.STATUS_ICON[-2] = 'help';
window.STATUS_ICON[-1] = 'remove';
window.STATUS_ICON[0] = 'check';
window.STATUS_ICON[1] = 'remove';
window.STATUS_ICON[2] = 'remove';
window.STATUS_ICON[3] = 'remove';
window.STATUS_ICON[4] = 'remove';
window.STATUS_ICON[5] = 'remove';
window.STATUS_ICON[6] = 'warning';
window.STATUS_ICON[7] = 'remove';
window.STATUS_ICON[8] = 'remove';
window.STATUS_ICON[11] = 'remove';
window.STATUS_ICON[12] = 'check';

window.LANGUAGE_DISPLAY = {
  'c': 'C',
  'cpp': 'C++11',
  'python': 'Python 3',
  'java': 'Java 8',
  'cc14': 'C++14',
  'cs': 'C#',
  'py2': 'Python 2',
  'php': 'PHP 7',
  'perl': 'Perl',
  'hs': 'Haskell',
  'js': 'Javascript',
  'ocaml': 'OCaml',
  'pypy': 'PyPy',
  'pas': 'Pascal',
  'rs': 'Rust'
};

$.parseStatusDisplay = function () {
  $("h5.ui.header.status-span").each(function () {
    var status = parseInt($(this).data('status'));
    var icon = '<i class="icon circle fitted ' + STATUS_ICON[status] + '"></i>';
    if ($(this).hasClass("with-icon"))
      $(this).html(icon + STATUS[status]);
    else
      $(this).html(STATUS[status]);
    $(this).addClass(STATUS_COLOR[status]);
    if (status != 0) {
      $(this).css("font-weight", 600);
    }
  });
  $("span.status-icon").each(function () {
    var status = parseInt($(this).data('status'));
    var icon = $(this).find('i.icon');
    icon.addClass(STATUS_COLOR[status]);
    icon.addClass(STATUS_ICON[status]);
  });
};

$.parseStatusDisplay();
