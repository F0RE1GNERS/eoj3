$(".ui.progress").each(function () {
  if ($(this).data("status")) {
    var status = $(this).data("status");
    if (status > 0) $(this).progress({ percent: 100 });
    else $(this).progress({ percent: 0 });
  }
});

var timer = setInterval(function() {
  function fixedTwo(number) {
    if (number == 0) return "00";
    return number < 10 ? ("0" + number) : ("" + number);
  }

  var countdowns = $(".countdown");
  countdowns.each(function () {
    var seconds = Math.floor($(this).data("delta-seconds")) - 1;
    $(this).data("delta-seconds", seconds);
    var show_time = Math.floor(seconds / 3600) + ":" + fixedTwo(Math.floor((seconds % 3600) / 60)) + ":" + fixedTwo(seconds % 60);
    $(this).html(show_time);
    if (seconds <= 0) {
      clearInterval(timer);
      $('#refreshNotification').modal('show');
    }

    var progress = $(this).closest(".ui.progress");
    var now_progress = 0;
    if ($(this).data("duration") > 0) {
      now_progress = 100 - $(this).data('delta-seconds') / $(this).data('duration') * 100;
      progress.progress({
        percent: now_progress
      });
    }
  });

}, 1000);
