$(function() {
  "use strict";

  horizon.modals.addModalInitFunction(muranoMoreLess);

  function muranoMoreLess(modal) {
    var showChar = 150;
    var ellipsestext = "...";
    var moretext = gettext("Show more");
    var lesstext = gettext("Show less");

    $(modal).find('.more_dynamicui_description').each(function() {
      var content = $.trim($(this).html());

      if (content.length > showChar) {

        var c = content.substr(0, showChar);
        var h = content.substr(showChar, content.length - showChar);

        var html = c + '<span class="more_ellipses_dynamicui">' + ellipsestext +
          '&nbsp;</span><span class="more_content_dynamicui"><span>' + h +
          '</span>&nbsp;&nbsp;<a href="javascript:;" class="more_link_dynamicui">' + moretext +
          '</a></span>';

        $(this).html(html);
      }
    });

    $(modal).find(".more_link_dynamicui").click(function() {
      if ($(this).hasClass("less_dynamicui")) {
        $(this).removeClass("less_dynamicui");
        $(this).html(moretext);
      } else {
        $(this).addClass("less_dynamicui");
        $(this).html(lesstext);
      }
      $(this).parent().prev().toggle();
      $(this).prev().toggle();
      return false;
    });
  }
});
