<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Catalog - KEEPER</title>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<meta name="keywords" content="File Collaboration Team Organization" />
<link rel="icon" type="image/x-icon" href="https://keeper.mpdl.mpg.de/media/img/favicon.png?t=1465786517" />
<!--[if IE]>
<link rel="shortcut icon" href="https://keeper.mpdl.mpg.de/media/img/favicon.png?t=1465786517"/>
<![endif]-->
<link rel="stylesheet" type="text/css" href="https://keeper.mpdl.mpg.de/media/css/seahub.min.css?t=1465786517" />
<link rel="stylesheet" type="text/css" href="https://keeper.mpdl.mpg.de/media/custom/keeper.css" />
<style>
	.item-block {
		box-sizing:border-box;
		border-bottom:1px solid #dddddd;
		display:block;
		width:100%;
		padding:10px 10px 10px 45px;
	}
	.item-block img {
		float:left;
		margin-top:4px;
		margin-left:-35px;
		width:20px;
	}
	.item-block h3,
	.item-block p {
		margin: 0;
		padding: 0;
	}
	a.pagination {
		display:inline-block;
		padding:5px 10px;
	}
	a.pagination.active {
		background-color:#57a5b8;
		color:#ffffff;
	}
	a.pagination:hover {
		background-color:#f4efde;
		text-decoration:none;
	}
	a.lib {
		/padding-left:10px !important;
	}
	a.lib:hover {
		text-decoration:none;
	}
	.errmsg {
		color:#cc0000;
	}
	span.disabled {
		padding:5px 10px;
		color:#cccccc;
		font-weight: bold;
	}

	#header {
   		background: #f4f4f7 !important;
    		width: 100% !important;
    		height: 32px !important;
   		font-size: 14px !important;
    		border-bottom: 1px solid #e8e8e8 !important;
    		padding-bottom: 4px !important;
    		z-index: 1 !important;
	}

	#logo{position: absolute; top: 13px !important; left: 16px !important;}
</style>
</head>

<body>
    <div id="wrapper" class="en">

        <div id="header">
            <div id="header-inner">
                
                <a href="/" id="logo" class="fleft">
                    
                    <img src="/media/%logo_path%" title="Catalog" alt="logo" width="140" height="40" />
                    
                </a>
                
                 
                <!--<div class="fright" id="lang">
                    <a href="#" id="lang-context" data-lang="en">English <span class="icon-caret-down"></span></a>
                    <ul id="lang-context-selector" class="hide">
                        
                        <li><a href="https://keeper.mpdl.mpg.de/i18n/?lang=de">Deutsch</a></li>
                        
                        <li><a href="https://keeper.mpdl.mpg.de/i18n/?lang=en">English</a></li>
                        
                    </ul>
                </div>
                -->
                
            </div>
        </div>

        <div id="main" class="clear">
            <div id="title-panel" class="w100 ovhd">
            </div>
            
            {contents}
			{data-nav}
            <!--<div id="left-panel" class="side-tabnav hide" role="navigation" style="display: block;">-->
                
                <!--<h3 class="hd">Institute</h3>-->
                <!--<ul class="side-tabnav-tabs">-->
                    <!--<li class="tab tab-cur"><a href="#" class="lib">Alle</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut A</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut B</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut C</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut D</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut E</a></li>-->
                <!--</ul>-->
                
            <!--</div>-->
            <div id="right-panel">
            	    <div class="hd ovhd">
						<h3 class="fleft">Project Catalog</h3>
						<!--<button class="repo-create btn-white fright"><span aria-hidden="true" class="icon-plus-square add vam"></span><span class="vam">New Library</span></button>-->
					</div>
			{/data-nav}
					
					
					{dataset}
						<div class="item-block">
							<h3>%title%</h3>
							<p>%smalltext%</p>
							<p>%author%</p>
                            %year%
							<p>Contact: %contact%</p>
						</div>
					{/dataset}
					{dataset_certified}
						<div class="item-block">
							<img src="static/certified.png" />
							<h3>%title%</h3>
							<p>%smalltext%</p>
							<p>%author%</p>
                            %year%
							<p>Contact: %contact%</p>
						</div>
					{/dataset_certified}
                    
                    {fyear} 
                        <p>Year: %year%</p>
                    {/fyear}
					
					{pagination-start}
						<p style="text-align:center;%style%">
					{/pagination-start}
					
					{page-prev}
						<a class="pagination" href="index.py?page=%page%">Previous</a>
					{/page-prev}
					{page-prev-disabled}
						<span class="disabled">Previous</span>
					{/page-prev-disabled}
					
					{pagination}
						<a class="pagination %cssclass%" href="index.py?page=%page%">%page%</a>
					{/pagination}
					
					{page-next}
						<a class="pagination" href="index.py?page=%page%">Next</a>
					{/page-next}
					{page-next-disabled}
						<span class="disabled">Next</span>
					{/page-next-disabled}
					
					{pagination-end}
						</p>
					{/pagination-end}
				
			{data-nav-end}
            </div>
			{/data-nav-end}
			{/contents}
			
            <div id="main-panel" class="clear w100 ovhd">
				<h3 class="errmsg" style="max-width:450px;text-align:center;margin:auto;padding:50px 0;">%errmsg%</h3>
            </div>
        </div>

    </div>
</div>

<script type="text/javascript" href="https://keeper.mpdl.mpg.de/media/js/jquery-1.12.1.min.js"></script>
<script type="text/javascript" href="https://keeper.mpdl.mpg.de/media/assets/scripts/lib/jquery.simplemodal.67fb20a63282.js"></script>
<script type="text/javascript" href="https://keeper.mpdl.mpg.de/media/assets/scripts/lib/jquery.ui.tabs.7406a3c5d2e3.js"></script>
<script type="text/javascript" href="https://keeper.mpdl.mpg.de/media/js/jq.min.js"></script>
<script type="text/javascript" href="https://keeper.mpdl.mpg.de/media/js/base.js?t=1465786517"></script>
<script type="text/javascript">
$.jstree._themes = 'https://keeper.mpdl.mpg.de/media/js/themes/';
function ajaxErrorHandler(xhr, textStatus, errorThrown) {
    if (xhr.responseText) {
        feedback($.parseJSON(xhr.responseText).error||$.parseJSON(xhr.responseText).error_msg, 'error');
    } else {
        feedback("Failed. Please check the network.", 'error');
    }
}
 
(function() {
    var lang_context = $('#lang-context'),
        lang_selector = $('#lang-context-selector');

    lang_context.parent().css({'position':'relative'});
    lang_selector.css({
        'top': lang_context.position().top + lang_context.height() + 5,
        'right': 0
        });

    lang_context.click(function() {
        lang_selector.toggleClass('hide');
        return false;
    });

    $(document).click(function(e) {
        var element = e.target || e.srcElement;
        if (element.id != 'lang-context-selector' && element.id != 'lang-context') {
            lang_selector.addClass('hide');
        }
    });
})();
</script>
</body>

<div id="lg_footer" style="border-top: 1px solid #DCDCDC; width: 61.5% ; height: 150px; position: relative; top: 86%; left: 22.5%;">
	<div style="height:80%; width: 20%; position: absolute; left:0%; top: 10%;">
		<h4 style="color: #57a5b8;">What you need to know</h4>
		<a class="normal" style="color: #B7B7B7;  font-weight: lighter;" href="https://keeper.mpdl.mpg.de/f/d17ecbb967/" target="_blank">About Keeper</a></br>
		<a style="color: #B7B7B7; font-weight: lighter;" href="https://keeper.mpdl.mpg.de/f/1b0bfceac2/" target="_blank">Cared Data Commitment</a></br>
		<a style="color: #B7B7B7; font-weight: lighter;" href="/catalog" target="_blank">Project Catalog</a></br>
		<a style="color: #B7B7B7; font-weight: lighter;" href="https://keeper.mpdl.mpg.de/f/f62758e53c/" target="_blank">Terms of Services</a></br></br></br></br>	
	</div>
	<div style="height:80%; width: 20%; position: absolute; left:27%; top: 10%;">
		<h4 style="color: #57a5b8;">Desktop client </h4>
		<a style="color: #B7B7B7;  font-weight: lighter;" href="/download_client_program/" target="_blank">Download the Keeper client for Windows, Linux and Mac</a>
		</br></br></br></br></br>
	</div>
	<div style="height:80%; width: 20%; position: absolute; right:27%; top: 10%;">
		<h4 style="color: #57a5b8;">The software behind Keeper</h4>
		<img id="seafile-logo" style="height: 30px; width: auto;"
		     src="/media/custom/seafile_logo_footer.png" onclick="window.open('https://www.seafile.com/en/home/');"/></br>
		<a style="color: #B7B7B7;  font-weight: lighter;" href="https://www.seafile.com/en/home/" target="_blank">© 2017 Seafile</a></br></br></br></br>		
	</div>
	<div style="height:80%; width: 20%; position: absolute; right:0%; top: 10%;">
		<h4 style="color: #57a5b8;" >A service by</h4>
		<img id="lg_ft" src="/media/custom/mpdl.png" style="height: 30px; width: auto;" onclick="window.open('https://www.mpdl.mpg.de/');"/></br>
		<a style="color: #B7B7B7;  font-weight: lighter;" href="mailto:keeper@mpdl.mpg.de">Contact Keeper Support</a></br>
		<a style="color: #B7B7B7;  font-weight: lighter;" href="https://keeper.mpdl.mpg.de/f/17e4e9d648/" target="_blank">Impressum</a>	
	</div>
</div>

</html>

