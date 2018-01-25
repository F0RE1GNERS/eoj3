$('.ui.checkbox:not(.vue)')
  .checkbox()
;
$('.ui.selection.dropdown, select.ui.selection, #navbar-small>.dropdown')
  .dropdown()
;
$('.ui.selection.dropdown.maximum-5')
  .dropdown({
    maxSelections: 5
  });
$('.ui.dropdown.onhover').dropdown({
  on: 'hover'
});
$('.message .close')
  .on('click', function() {
    $(this)
      .closest('.message')
      .transition('fade')
    ;
    if ($(this).data('close-action')) {
      $.post($(this).data('close-action'), {
        'csrfmiddlewaretoken': Cookies.get('csrftoken')
      });
    }
  })
;
$(".ui.file.input").inputFile();
$('.ui.tabular.menu .item').tab();

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
$('.ui.search.dropdown.submit')
  .dropdown();

// user search
$('.ui.search.user').search({
  apiSettings: {
    url: '/api/search/user/?kw={query}'
  },
  fields: {
    title: 'name'
  },
  minCharacters: 1
});

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

$.filterChangeTo = function (filter, value) {
  var obj = getUrlParamAsObject();
  var originalObj = $.extend({}, obj);
  if (value == 'all')
    value = '';
  if (!value && obj.hasOwnProperty(filter)) {
    delete obj[filter];
  } if (value) {
    obj[filter] = value;
  }
  if (!_.isEqual(obj, originalObj)) {
    location.href = encodeObjectAsUrlParamString(obj);
  }
};

$('.ui.dropdown.status-filter').each(function () {
  var api_url = null;
  if ($(this).data('filter-type') == 'user' && !$(this).hasClass("local")) {
    if ($(this).data('filter-contest'))
      api_url = '/api/search/user/?kw={query}&contest=' + $(this).data('filter-contest');
    else api_url = '/api/search/user/?kw={query}';
  } else if ($(this).data('filter-type') == 'problem' && !$(this).hasClass("local"))
    api_url = '/api/search/problem/?kw={query}';
  $(this).dropdown({
    onChange: function (value) {
      $.filterChangeTo($(this).data('filter-type'), value);
    }.bind(this),
    apiSettings: api_url ? {
      url: api_url
    } : false
  });
});

$('.restore')
  .click(function (event) {
    var dropdown = $(event.currentTarget).prev(".ui.dropdown.status-filter");
    dropdown.dropdown('restore defaults');
    $.filterChangeTo(dropdown.data('filter-type'), '');
  });

$('.ui.dropdown.user-search')
  .dropdown({
    apiSettings: {
      url: $(this).data('query') || '/api/search/user/?kw={query}'
    }
  })
;

$('.ui.dropdown.problem-search')
  .dropdown({
    apiSettings: {
      url: $(this).data('query') || '/api/search/problem/?kw={query}'
    }
  });

// function post and modal related
function postWithLocalData (button) {
  var link = button.data('link');
  var data = button.data();
  data['csrfmiddlewaretoken'] = Cookies.get('csrftoken');
  $.post(link, data, function (data) {
      location.reload();
    }
  );
}

function replaceFormData(form, extra_data) {
  for (var val in extra_data) {
    if (extra_data.hasOwnProperty(val)) {
      var already_exist = form.find('*[name="' + val + '"]');
      if (already_exist.length > 0) {
        if (already_exist.prop("tagName") == "SELECT") {
          already_exist.parent(".ui.dropdown").dropdown("set selected", extra_data[val]);
        } else {
          already_exist.val(extra_data[val]);
        }
      } else {
        form.append("<input type='hidden' name='" + val + "' value='" + extra_data[val] + "'>");
      }
    }
  }
}

$(".post-link")
  .on('click', function(e) {
    postWithLocalData($(e.currentTarget));
  })
  .attr('href', 'javascript:void(0)');

$(".like-link")
  .on('click', function(e) {
    function add (selector, value) {
      selector.text(parseInt(selector.text()) + value);
    }

    var button = $(e.currentTarget);
    var link = button.data('link');
    $.post(link, {
      'csrfmiddlewaretoken': Cookies.get('csrftoken'),
      'comment': button.data('comment'),
      'flag': button.data('flag')
    }, function (data) {
      var span = button.find('span');
      if (span.length) {
        if (data) {
          button.find('i.thumbs').removeClass("outline");
          button.find('i.heart').removeClass('empty');
          add(span, 1);
          var siblingSpan = button.siblings('.like-link');
          if (!siblingSpan.find('i.thumbs').hasClass("outline")) {
            siblingSpan.find('i.thumbs').addClass("outline");
            add(siblingSpan.find('span'), -1);
          }
        } else {
          button.find('i.thumbs').addClass("outline");
          button.find('i.heart').addClass('empty');
          add(span, -1);
        }
      } else { location.reload(); }
    });
  });

$(".comment .actions .reply").each(function () {
  $(this).on('click', function () {
    $(".ui.form input[name='reply_to']").val($(this).data("pk"));
    $(".ui .reply-to-name").text($(this).parent().siblings(".user").text());
    $('html, body').animate({
      scrollTop: $(".ui.form").offset().top - $("#navbar").height() - 15
    }, 500);
  }.bind(this));
});


$(".clear-reply-to")
  .on('click', function(e) {
    $(".ui.form input[name='reply_to']").val('0');
    $(".ui .reply-to-name").text('the post');
  });


$(".reply-to").insertAfter(".autosave");

$(".delete-link")
  .on('click', function (e) {
    $("#delete-confirmation")
      .modal({
        onApprove: function () {
          postWithLocalData($(e.currentTarget));
        }
      })
      .modal('show');
  })
  .attr('href', 'javascript:void(0)');

$(".modal-link")
  .on('click', function (e) {
    var button = $(e.currentTarget);
    var modal = $(button.data('target'));
    if (button.data('action'))
      modal.find("form").attr("action", $(e.currentTarget).data('action'));
    if (modal.find("form").length > 0)
      replaceFormData(modal.find("form"), button.data());
    modal
      .modal({
        onApprove: function () {
          var form = $(this).find("form");
          var data = new FormData(form[0]);
          $.ajax({
            url: form.attr("action"),
            type: 'POST',
            data: data,
            processData: false,
            contentType: false,
            complete: function () {
              location.reload();
            }
          });
        }
      })
      .modal('show');
  })
  .attr('href', 'javascript:void(0)');

$(".ui.checkbox.immediate")
  .checkbox({
    onChange: function () {
      postWithLocalData($(this));
    }
  });

$(".penalty-box").on('dblclick', function (e) {
  var penaltyModal = $("#penalty-detail-modal");
  penaltyModal.modal({
    observeChanges: true
  }).modal('show');
  var content = penaltyModal.find(".content");
  content.html('');
  $.get(penaltyModal.data('api') + $(e.currentTarget).data('param'), function (data) {
    content.html(data);
    $.parseStatusDisplay();
  });
});

$(".ui.backend.sortable.table").each(function () {
  var url_param = getUrlParamAsObject();
  $(this).find("thead th").each(function () {
    var d_type = $(this).data("key");
    var next_type = $(this).data("order");
    if (url_param.hasOwnProperty("c") && url_param.hasOwnProperty("a") && d_type == url_param.c) {
      $(this).addClass("sorted " + url_param.a);
      next_type = url_param.a == "ascending" ? "descending" : "ascending";
    }
    var new_url_param = _.assign({}, url_param);
    new_url_param.c = d_type;
    new_url_param.a = next_type;
    $(this).on('click', function () {
      location.href = encodeObjectAsUrlParamString(new_url_param);
    })
  })
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
  $("h5.ui.header.status-span, .status-label").each(function () {
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
  new Clipboard('.clipboard');
};

// initialize
$(document).ready(function () {
  $.parseStatusDisplay();
});

function copyToClipboard(text) {
  if (window.clipboardData && window.clipboardData.setData) {
        // IE specific code path to prevent textarea being shown while dialog is visible.
        return clipboardData.setData("Text", text);

    } else if (document.queryCommandSupported && document.queryCommandSupported("copy")) {
        var textArea = document.createElement("textarea");
        textArea.textContent = text;

        // Place in top-left corner of screen regardless of scroll position.
        textArea.style.position = 'fixed';
        textArea.style.top = 0;
        textArea.style.left = 0;

        // Ensure it has a small width and height. Setting to 1px / 1em
        // doesn't work as this gives a negative w/h on some browsers.
        textArea.style.width = '2em';
        textArea.style.height = '2em';

        // We don't need padding, reducing the size if it does flash render.
        textArea.style.padding = 0;

        // Clean up any borders.
        textArea.style.border = 'none';
        textArea.style.outline = 'none';
        textArea.style.boxShadow = 'none';

        // Avoid flash of white box if rendered for any reason.
        textArea.style.background = 'transparent';

        document.body.appendChild(textArea);
        textArea.select();
        try {
            return document.execCommand("copy");  // Security exception may be thrown by some browsers.
        } catch (ex) {
            console.warn("Copy to clipboard failed.", ex);
            return false;
        } finally {
            document.body.removeChild(textArea);
        }
    }
}