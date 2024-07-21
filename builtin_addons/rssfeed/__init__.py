from pipeline_backend import *
import feedparser
import traceback

from pipeline_backend.commands_builtin import yield_for_seconds

# RSS Spec https://www.rssboard.org/rss-specification#requiredChannelElements

@Commands.register_command
def rssfeed_get_entries(instance:Instance,feed_url:URL,output_list_name:VariableName) -> CommandReturnStatus:
    # gets all the items in an rssfeed at the given url and saves it to a variable, the first item being the oldest, the last being the newest

    try:
        parser = feedparser.parse(feed_url.value)
    except Exception as e:
        instance.log_line(traceback.format_exc())
        # Try again later, it is likely only a transitory problem
        yield_for_seconds(instance,Integer(60))
        return CommandReturnStatus.Yield | CommandReturnStatus.Keep_Position

    if len(parser.entries) == 0:
        instance[output_list_name] = VariableList()
        return CommandReturnStatus.Success

    # parse out entries in the feed for the information we want
    entries = VariableList()
    for entry in parser.entries:
        parsed_entry :dict[str,WorkVariable] = {}
        if "title" in entry:
            parsed_entry["title"] = String(entry["title"])
        if "link" in entry:
            parsed_entry["link"] = URL(entry["link"])
        if "summary" in entry:
            parsed_entry["summary"] = String(entry["summary"])
        if "id" in entry:
            parsed_entry["id"] = String(entry["id"])
        if "published" in entry:
            # Lets convert it into the iso format
            # example - Sun, 07 Jul 2024 09:31:45 -0000
            dt = datetime.strptime(entry["published"],"%a, %d %b %Y %H:%M:%S %z")
            parsed_entry["published"] = String(dt.isoformat())
        entries.value.append(Dictionary(parsed_entry))
    
    # Sort the entries from oldest to newest - yes, most feeds are newest first, but never trust unknown input to be sorted
    # Of course, since *most* are in the reverse order, just reverse the entries right now before sorting to be a little more efficent
    entries.value.reverse()
    if "published" in entries.value[0].value:
        entries.value.sort(key=lambda variable: datetime.fromisoformat(variable.value['published'].value))

    instance[output_list_name] = entries
    return CommandReturnStatus.Success

@Commands.register_command
def rssfeed_trim_entries_with_checkpoint(instance:Instance,entry_list_name:VariableName,checkpoint_id:VariableName) -> CommandReturnStatus:
    # trims off all items that are before or at the checkpoint_id and then updates the checkpoint id to the newest for subsequent calls
    # Remember that all entries are Dictionary() objects

    entry_list : VariableList = instance[entry_list_name]
    if len(entry_list.value) == 0:
        return CommandReturnStatus.Success

    # we need to save the last item's id for the next time we check - we save it before the trimming since it might be a trim of the whole list
    last_entry_id = String()
    if "id" in entry_list.value[-1].value:
        last_entry_id = entry_list.value[-1].value["id"]
    elif "link" in entry_list.value[-1].value:
        last_entry_id = entry_list.value[-1].value["link"]
    else:
        instance.log_line("Rss Feed Entries seem to be lacking an 'id' or 'link' fields and so we have no reliable way to track things.")
        return CommandReturnStatus.Error

    if checkpoint_id in instance:
        # we have a checkpoint id to actually compare against so lets find it and trim
        found_idx = None
        previd = instance[checkpoint_id].value
        for idx,entry in enumerate(entry_list.value):
            if "id" in entry.value:
                if previd == entry.value["id"].value:
                    found_idx = idx
                    break
            elif "link" in entry.value:
                if previd == entry.value["link"].value:
                    found_idx = idx
                    break
            else:
                instance.log_line("Rss Feed Entries seem to be lacking an 'id' or 'link' fields and so we have no reliable way to track things.")
                return CommandReturnStatus.Error
        if found_idx != None:
            # slice and save
            entry_list.value = entry_list.value[found_idx+1:]
            instance[entry_list_name] = entry_list
    
    instance[checkpoint_id] = last_entry_id
    return CommandReturnStatus.Success