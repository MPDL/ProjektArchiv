<!DOCTYPE html>
<head>
<title>Catalog - KEEPER</title>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<meta name="keywords" content="File Collaboration Team Organization" />
<link rel="icon" type="image/x-icon" href="/media/img/favicon.png?t=1465786517" />
<!--[if IE]>
<link rel="shortcut icon" href="https://keeper.mpdl.mpg.de/media/img/favicon.png?t=1465786517"/>
<![endif]-->
<link rel="stylesheet" type="text/css" href="/media/assets/css/bootstrap.min.css"/>
<link rel="stylesheet" type="text/css" href="/media/css/seahub.min.css?t=1465786517" />
<link rel="stylesheet" type="text/css" href="/media/custom/__BRANDING_CSS__" />
<style>

    body {
        overflow-x: hidden;
        overflow-y: auto;
    }

    #header {
        padding-top: 16px;
        margin-bottom: 20px;
   		background: #f4f4f7 !important;
        width: 100% !important;
        font-size: 14px !important;
        border-bottom: 1px solid #e8e8e8 !important;
        padding-bottom: 4px !important;
        z-index: 1 !important;
	}
	#header-inner {
		height: 48px;
		width: 950px;
		margin: 0 auto;
	}
	#logo{
        position: absolute; 
        top: 13px !important; 
        left: 16px !important;
        margin-top: -5px;
    }

	#main {
        min-height: 400px;
        margin: 0 auto;

    }
    .side-tabnav h3 {
        margin-top: 65px !important;
        color: #57a5b8 !important;
    }
    .side-tabnav label {
        margin-top: 0px;
    }
    .side-tabnav span.vam {
        margin-left: 5px;
    }
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
		color:#ffffff !important;
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
    #lg_footer h4 {
        color: #57a5b8 !important;
    }
    #keeper-links {
        margin-top: 10px;
    }
    #seafile-credits {
        margin-top: 5px;
        text-align: center;
    }
       
</style>
</head>

<body>
    <div id="wrapper" class="en">
        <div id="header">
            <div id="header-inner">
                <a href="/" id="logo" class="fleft">
                    <img src="/media/%logo_path%" title="Catalog" alt="logo" width="140" height="40" />
                </a>
            </div>
        </div>
        
        <div class="container">
            <div id="main" class="raw clear">

                {contents}
                {data-nav}
                <div id="left-panel" class="col-md-3 side-tabnav">

                    <h3 class="hd">Show Projects</h3>
                    <form id="scope-selector" method="post">
                        <label class="radio-item">
                            <input class="vam" type="radio" name="cat_scope" value="with_metadata" %checked_with_metadata%/><span class="vam">with metadata</span>
                        </label>
                        <br>
                        <label class="radio-button">
                            <input class="vam" type="radio" name="cat_scope" value="with_certificate" %checked_with_certificate%/><span class="vam">with certificate</span>
                        </label>
                        <br>
                        <label class="radio-button">
                            <input class="vam" type="radio" name="cat_scope" value="all" %checked_all%/><span class="vam">all</span>
                        </label>
                    </form>
                    <!--<ul class="side-tabnav-tabs">-->
                    <!--<li class="tab tab-cur"><a href="#" class="lib">Alle</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut A</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut B</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut C</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut D</a></li>-->
                    <!--<li class="tab"><a href="#" class="lib">Institut E</a></li>-->
                    <!--</ul>-->

                </div>
                <div class="col-md-9" id="right-panel">
                    <div class="hd ovhd">
                        <h3 class="fleft">The Keeper Project Catalog of the Max Planck Society</h3>
                    </div>
                    {/data-nav}


                    {dataset}
                    <div class="item-block">
                        <h3>%title%</h3>
                        <p>%smalltext%</p>
                        <p>%author%</p>
                        %year%
                        <p>Contact: %contact%</p>
                        %landing_page_url%
                    </div>
                    {/dataset}
                    {dataset_certified}
                    <div class="item-block">
                        <img src="/catalog/static/certified.png" />
                        <h3>%title%</h3>
                        <p>%smalltext%</p>
                        <p>%author%</p>
                        %year%
                        <p>Contact: %contact%</p>
                        %landing_page_url%
                    </div>
                    {/dataset_certified}

                    {flanding_page_url}
                        <p><a href="%landing_page_url%">Landing Page</a></p>
                    {/flanding_page_url}

                    {ftitle}
                        <a href="%landing_page_url%">%title%</a>
                    {/ftitle}

                    {fyear}
                    <p>Year: %year%</p>
                    {/fyear}

                    {pagination-start}
                    <p style="text-align:center;%style%">
                        {/pagination-start}

                        {page-prev}
                            <a class="pagination" href="/catalog/index.py?page=%page%&scope=%scope%">Previous</a>
                        {/page-prev}
                        {group-prev}
                            <a class="group-prev" href="/catalog/index.py?page=%page%&scope=%scope%">...</a>
                        {/group-prev}

                        {pagination}
                            <a class="pagination %cssclass%" href="/catalog/index.py?page=%page%&scope=%scope%">%page%</a>
                        {/pagination}

                        {group-next}
                            <a class="group-next" href="/catalog/index.py?page=%page%&scope=%scope%">...</a>
                        {/group-next}
                        {page-next}
                            <a class="pagination" href="/catalog/index.py?page=%page%&scope=%scope%">Next</a>
                        {/page-next}
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
</div>

    %footer%   


    <script type="text/javascript" src="/media/assets/scripts/lib/jquery.min.js" id="jquery"></script>
    <script type="text/javascript">
        $('#scope-selector').click(function( event ) {
            var form = $( this ),
                target = $( event.target )
            if ( target.is('input') && !target.attr('checked') ) {
                $.post("/catalog/", form.serialize(), function(){
                    form.submit();
                });
            }
        });

        function ajaxErrorHandler(xhr, textStatus, errorThrown) {
            if (xhr.responseText) {
                feedback($.parseJSON(xhr.responseText).error||$.parseJSON(xhr.responseText).error_msg, 'error');
            } else {
                feedback("Failed. Please check the network.", 'error');
            }
        }
    </script>
    <!-- Start of mpdl Zendesk Widget script -->
    <script id="ze-snippet" src="https://static.zdassets.com/ekr/snippet.js?key=32977f9b-455d-428b-8dd5-f4c65aad0daa"> </script>
    <!-- End of mpdl Zendesk Widget script -->
</body>


</html>

