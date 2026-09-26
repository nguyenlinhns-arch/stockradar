    // >>> V7_MXH_PUBLISH_INTEGRATION
    JsonArray mxhEditedVideos=new();
    string mxhPlanId="";

    async Task<JsonObject> MxhCall(string action,JsonObject? arguments=null)
    {
        arguments??=new JsonObject();
        var bridge=new JsonObject{["action"]=action,["arguments"]=arguments};
        var result=await client.CallTool("pc.execute_task",new JsonObject{
            ["goal"]="MXH_V1:"+bridge.ToJsonString(Platform.JsonOptions),
            ["request_id"]=Guid.NewGuid().ToString()
        });
        if(result["ok"]?.GetValue<bool>()!=true)
            throw new InvalidOperationException(result["error"]?.ToString()??result.ToJsonString(Platform.JsonOptions));
        return result;
    }

    async void MxhRefresh(object s,RoutedEventArgs e)=>await Guard(async()=>
    {
        var response=await MxhCall("list_edited",new JsonObject{["limit"]=200});
        var payload=response["result"] as JsonObject??new JsonObject();
        mxhEditedVideos=payload["entries"] as JsonArray??new JsonArray();
        var rows=mxhEditedVideos.OfType<JsonObject>()
            .Select(v=>new KeyValuePair<string,string>(
                v["artifact_job_id"]?.ToString()??"",
                v["title"]?.ToString()??v["name"]?.ToString()??""
            )).Where(v=>v.Key!="").ToList();
        MxhVideoCombo.ItemsSource=rows;
        if(rows.Count>0)MxhVideoCombo.SelectedIndex=0;
        if(string.IsNullOrWhiteSpace(MxhDate.Text))MxhDate.Text=DateTime.Now.AddDays(1).ToString("yyyy-MM-dd");
        MxhStatus.Text=$"Hub catalog: {rows.Count} video đã edit.";
    });

    void MxhVideoChanged(object s,SelectionChangedEventArgs e)
    {
        string id=MxhVideoCombo.SelectedValue?.ToString()??"";
        var row=mxhEditedVideos.OfType<JsonObject>().FirstOrDefault(v=>v["artifact_job_id"]?.ToString()==id);
        if(row!=null)MxhTitle.Text=row["title"]?.ToString()??row["name"]?.ToString()??"";
        mxhPlanId="";
        MxhReceipt.Text="";
    }

    int MxhFlowId()
    {
        if(MxhFlow.SelectedItem is ComboBoxItem item&&int.TryParse(item.Tag?.ToString(),out int value)&&(value==1||value==2))return value;
        return 2;
    }

    JsonArray MxhPlatforms()
    {
        var rows=new JsonArray();
        if(MxhTikTok.IsChecked==true)rows.Add("tiktok");
        if(MxhFacebook.IsChecked==true)rows.Add("facebook");
        if(MxhYoutube.IsChecked==true)rows.Add("youtube");
        if(rows.Count==0)throw new InvalidOperationException("Chọn ít nhất một nền tảng.");
        if(MxhFlowId()!=2&&rows.Any(v=>v?.ToString()=="youtube"))throw new InvalidOperationException("YouTube chỉ dùng ở Luồng 2.");
        return rows;
    }

    string MxhScheduledAt()
    {
        if(!DateTime.TryParseExact(
            MxhDate.Text.Trim()+" "+MxhTime.Text.Trim(),
            "yyyy-MM-dd HH:mm",
            System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.None,
            out var local))
            throw new InvalidOperationException("Ngày/giờ phải theo yyyy-MM-dd và HH:mm.");
        var dto=new DateTimeOffset(DateTime.SpecifyKind(local,DateTimeKind.Unspecified),TimeSpan.FromHours(7));
        return dto.UtcDateTime.ToString("O");
    }

    JsonObject MxhSelected()
    {
        string id=MxhVideoCombo.SelectedValue?.ToString()??throw new InvalidOperationException("Chọn video.");
        return mxhEditedVideos.OfType<JsonObject>().FirstOrDefault(v=>v["artifact_job_id"]?.ToString()==id)
            ??throw new InvalidOperationException("Video không còn trong catalog Hub.");
    }

    static bool MxhVerified(JsonObject summary,IEnumerable<string> requested)
    {
        string raw=summary.ToJsonString(Platform.JsonOptions);
        foreach(string platform in requested)
        {
            if(!raw.Contains("\"platform\":\""+platform+"\"",StringComparison.OrdinalIgnoreCase))return false;
        }
        return raw.Contains("\"status\":\"scheduled\"",StringComparison.OrdinalIgnoreCase)
            &&raw.Contains("\"scheduleVerified\":true",StringComparison.OrdinalIgnoreCase);
    }

    async void MxhCreatePlan(object s,RoutedEventArgs e)=>await Guard(async()=>
    {
        var video=MxhSelected();
        string title=MxhTitle.Text.Trim();
        if(title=="")throw new InvalidOperationException("Thiếu tiêu đề.");
        var platforms=MxhPlatforms();
        var args=new JsonObject{
            ["artifact_job_id"]=video["artifact_job_id"]?.ToString()??"",
            ["title"]=title,
            ["caption"]=title,
            ["hashtags"]=MxhHashtags.Text.Trim(),
            ["platforms"]=platforms.DeepClone(),
            ["flow_id"]=MxhFlowId(),
            ["scheduled_at"]=MxhScheduledAt(),
            ["timezone"]="Asia/Ho_Chi_Minh"
        };
        var response=await MxhCall("create_or_reuse_plan",args);
        var plan=response["result"] as JsonObject??new JsonObject();
        mxhPlanId=plan["id"]?.ToString()??"";
        if(mxhPlanId=="")throw new InvalidOperationException("Hub chưa trả plan id.");
        MxhReceipt.Text=plan.ToJsonString(Platform.JsonOptions);
        bool nativeReady=plan["nativeScheduleReady"]?.GetValue<bool>()==true;
        MxhStatus.Text=nativeReady
            ?"Plan đã có native receipt; bấm Làm mới receipt để đối soát."
            :"Plan đã tạo/reuse; chưa đủ bằng chứng lịch native.";
    });

    async Task MxhReadReceipt()
    {
        if(string.IsNullOrWhiteSpace(mxhPlanId))throw new InvalidOperationException("Chưa có plan.");
        var response=await MxhCall("plan_readback",new JsonObject{["plan_id"]=mxhPlanId});
        var summary=response["result"] as JsonObject??new JsonObject();
        MxhReceipt.Text=summary.ToJsonString(Platform.JsonOptions);
        var platforms=MxhPlatforms().Select(v=>v?.ToString()??"").Where(v=>v!="").ToArray();
        MxhStatus.Text=MxhVerified(summary,platforms)
            ?"SCHEDULED_VERIFIED · Đã có bằng chứng lịch native."
            :"Chưa có SCHEDULED_VERIFIED · không tự gửi lại.";
    }

    async void MxhNativeSchedule(object s,RoutedEventArgs e)=>await Guard(async()=>
    {
        if(string.IsNullOrWhiteSpace(mxhPlanId))throw new InvalidOperationException("Tạo/dùng plan trước.");
        var before=await MxhCall("plan_readback",new JsonObject{["plan_id"]=mxhPlanId});
        var summary=before["result"] as JsonObject??new JsonObject();
        var platforms=MxhPlatforms();
        var names=platforms.Select(v=>v?.ToString()??"").Where(v=>v!="").ToArray();
        if(MxhVerified(summary,names))
        {
            MxhReceipt.Text=summary.ToJsonString(Platform.JsonOptions);
            MxhStatus.Text="SCHEDULED_VERIFIED · Không gửi lại.";
            return;
        }
        var response=await MxhCall("native_schedule",new JsonObject{
            ["plan_id"]=mxhPlanId,
            ["platforms"]=platforms.DeepClone(),
            ["timeout_seconds"]=1200
        });
        MxhReceipt.Text=(response["result"]??response).ToJsonString(Platform.JsonOptions);
        MxhStatus.Text="Đã gửi native schedule; đang chờ receipt xác minh.";
        await MxhReadReceipt();
    });

    async void MxhRefreshReceipt(object s,RoutedEventArgs e)=>await Guard(MxhReadReceipt);
    // <<< V7_MXH_PUBLISH_INTEGRATION
