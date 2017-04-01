var timer = setInterval(function() {
  function fixedTwo(number) {
    if (number == 0) return "00";
    return number < 10 ? ("0" + number) : ("" + number);
  }

  var countdowns = $(".countdown");
  for (var i = 0; i < countdowns.length; ++i) {
    var countdown = $(countdowns[i]);
    var seconds = countdown.data("delta-seconds") - 1;
    countdown.data("delta-seconds", seconds);
    var show_time = Math.floor(seconds / 3600) + ":" + fixedTwo(Math.floor((seconds % 3600) / 60)) + ":" + fixedTwo(seconds % 60);
    countdown.html(show_time);
    if (seconds <= 0) {
      clearInterval(timer);
      $('#refreshNotification').modal('show');
    }
  }

  // There is only one progress bar
  var progress = $(".countdown-progress");
  if (progress.data('status') == 'running') {
    progress.data('acc', progress.data('acc') + 1);
    var now_progress = Math.round(progress.data('acc') / progress.data('all') * 100);
    progress.css("width", now_progress + "%");
    progress.attr("aria-valuenow", now_progress);
  }


}, 1000);
