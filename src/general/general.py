import discord
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
from general.help_views import HelpView, HelpEmbed 
# from misc.achievement_views import AchievementUnlockedEmbed
from firebase_admin import db

"""
This cog contains miscellaneous commands not specific to any game.
"""

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_ref_users = db.reference("/").child("users")
        self.db_ref_attacks = db.reference("/").child("attacks")

    @app_commands.command(name="help", description="Info about commands, etc.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=HelpEmbed(), view=HelpView(), ephemeral=True)

    @app_commands.command(name="profile", description="View your profile")
    async def profile(self, interaction: discord.Interaction, user: discord.Member=None):
        # Deferring response to prevent timeout/exceptions
        await interaction.response.defer(ephemeral=True, thinking=True)

        if user is None:
            user = interaction.user

        profile_info = ""
        user_dictionary = self.db_ref_users.get()
        
        # list of attack Message Objects
        atk_msgs = []
        
        # list of defense Message Objects
        def_msgs = []
        
        if user_dictionary == None:
            profile_info = "No users have been logged"
        else:
            users_sorted = sorted(user_dictionary.items(), key=lambda x: x[1]["points"], reverse=True)
            rank = 1
            for key, value in users_sorted:
                if value["name"] == user.name:
                    break
                rank += 1
                
            specified_user = user_dictionary.get(str(user.id))
            if specified_user == None:
                profile_info = "Nothing to see here :) If this is you, please use `/editprofile` to set up your profile."
            else:
                v_username = specified_user.get("name")
                v_points = specified_user.get("points")
                
                sent_dictionary = specified_user.get("attacks_sent")
                v_sent = ""
                if sent_dictionary == None:
                    v_sent = "**N/A**\n"
                else:
                    for message_id in sent_dictionary:
                        message_url = f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/{message_id}"
                        v_sent += f"[{message_id}]({message_url})\n"
                        
                                                # add to list of attack Message Objects
                        try:
                            msg_obj = await interaction.channel.fetch_message(message_id)
                            atk_msgs.append(msg_obj)
                        except Exception as e:
                            print(f"Error fetching attack message: [{message_id}]")
                            print(e)
                            pass
                
                received_dictionary = specified_user.get("attacks_received")
                v_received = ""
                if received_dictionary == None:
                    v_received = "**N/A**\n"
                else:
                    for message_id in received_dictionary:
                        message_url = f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/{message_id}"
                        v_received += f"[{message_id}]({message_url})\n"
                        
                v_oclink = specified_user.get("oclink")
                #v_oclink = f"[{v_oclink}]({v_oclink})"
                v_notes = specified_user.get("notes")
                
                profile_info += f"User: **<@{user.id}>**\nPoints: **{v_points}**\nRank: **{rank}**\n\nAttacks Sent:\n{v_sent}\nAttacks Received:\n{v_received}\nOC Link:\n**{v_oclink}**\n\nNotes:\n**{v_notes}**\n"
                
        # Profile Embed
        embed_profile = discord.Embed(title='', description=profile_info, color=discord.Colour.light_embed())
        # embed_profile.set_thumbnail(url=user.avatar)
        embed_profile.set_author(name=f'{user.name}\'s Profile', icon_url=user.avatar)
        
        # pagination of attack images using left and right buttons
        view_images = View()
        # index and mode tracker
        view_images.index = 0
        view_images.mode = None
        atk_msgs_exist = atk_msgs and len(atk_msgs) > 0
        def_msgs_exist = def_msgs and len(def_msgs) > 0
        
        # atk and def image mode buttons |atk| |def|
        if atk_msgs_exist:
            view_images.add_item(Button(label="Attacks", style=discord.ButtonStyle.primary))
            view_images.mode = atk_msgs
        if def_msgs_exist:
            view_images.add_item(Button(label="Defenses", style=discord.ButtonStyle.primary))
            view_images.mode = def_msgs if view_images.mode == None else atk_msgs

        if view_images.mode:
            view_images.add_item(Button(label="<", style=discord.ButtonStyle.primary))
            view_images.add_item(Button(label=">", style=discord.ButtonStyle.primary))
            embed_profile.set_image(url=view_images.mode[view_images.index].embeds[0].image.url)
            embed_profile.set_footer(text=f"Art Fight Profile | {'Attacks Sent' if atk_msgs_exist else 'Attacks Recieved'}", icon_url=interaction.guild.icon.url)
            
            async def atk_button_callback(interaction: discord.Interaction):
                view_images.mode = atk_msgs
                view_images.index = 0
                embed_profile.set_image(url=view_images.mode[0].embeds[0].image.url)
                embed_profile.set_footer(text="Art Fight Profile | Attacks Sent", icon_url=interaction.guild.icon.url)
                await interaction.response.edit_message(embed=embed_profile, view=view_images)
            
            async def def_button_callback(interaction: discord.Interaction):
                view_images.mode = def_msgs
                view_images.index = 0
                embed_profile.set_image(url=view_images.mode[0].embeds[0].image.url)
                embed_profile.set_footer(text="Art Fight Profile | Attacks Received", icon_url=interaction.guild.icon.url)
                await interaction.response.edit_message(embed=embed_profile, view=view_images)
            
            async def next_button_callback(interaction: discord.Interaction):
                # edit embed image to next attack using index
                embed_profile.set_image(url=view_images.mode[(view_images.index+1) % len(view_images.mode)].embeds[0].image.url)
                view_images.index = (view_images.index+1) % len(view_images.mode)
                await interaction.response.edit_message(embed=embed_profile, view=view_images)
            
            async def prev_button_callback(interaction: discord.Interaction):
                # edit embed image to previous attack using index
                embed_profile.set_image(url=view_images.mode[(view_images.index-1) % len(view_images.mode)].embeds[0].image.url)
                view_images.index = (view_images.index-1) % len(view_images.mode)
                await interaction.response.edit_message(embed=embed_profile, view=view_images)
            
            view_children_indexer = 0
            if atk_msgs_exist:
                view_images.children[view_children_indexer].callback = atk_button_callback
                view_children_indexer += 1
            if def_msgs_exist:
                view_images.children[view_children_indexer].callback = def_button_callback
                view_children_indexer += 1
            view_images.children[view_children_indexer].callback = prev_button_callback
            view_images.children[view_children_indexer+1].callback = next_button_callback

        try:
            await interaction.followup.send("", embed=embed_profile, view=view_images, ephemeral=True)
        except Exception as e:
            print(f"Error sending profile embed: {e}")
            await interaction.followup.send("An error occured while trying to send the profile embed", ephemeral=True)

    @app_commands.command(name="editprofile", description="Add a link to your oc's and/or a description of your favorite things")
    async def editprofile(self, interaction: discord.Interaction, new_oc_link:str="", new_notes:str=""):
        user_dictionary = self.db_ref_users.get()
        
        if new_oc_link == "" and new_notes == "":
            await interaction.response.send_message("You didn't pass in any profile updates to make", ephemeral=True)
        elif user_dictionary == None:
            await interaction.response.send_message("No profiles are currently logged", ephemeral=True)
        elif not (str(interaction.user.id) in user_dictionary):
            await interaction.response.send_message("You aren't logged yet, you need to attack or be attacked in order to create a profile", ephemeral=True)
        else:

            if new_oc_link != "":
                self.db_ref_users.child(str(interaction.user.id)).child("oclink").delete()
                self.db_ref_users.child(str(interaction.user.id)).update({"oclink": new_oc_link})
            if new_notes != "":
                self.db_ref_users.child(str(interaction.user.id)).child("notes").delete()
                self.db_ref_users.child(str(interaction.user.id)).update({"notes": new_notes})
        
            await interaction.response.send_message("Links and Notes have been updated! (feel free to dismiss this message)", ephemeral=True)
        
    @app_commands.command(name="leaderboard", description="Shows an activity-based leaderboard for all the games")
    async def leaderboard(self, interaction: discord.Interaction):
        calculated_standings = ""
        top_3_counter = 1
        user_dictionary = self.db_ref_users.get()
        if user_dictionary == None:
            calculated_standings = "No one has attacked yet"
        else:
            users_sorted = sorted(user_dictionary.items(), key=lambda x: x[1]["points"], reverse=True)
            for key, value in users_sorted:
                if value["points"] == 0:
                    break
                
                if top_3_counter == 1:
                    v_name = value["name"]
                    v_points = value["points"]
                    calculated_standings += f"{top_3_counter} - 🥇 {v_name} - {v_points} points\n"
                    top_3_counter += 1
                elif top_3_counter == 2:
                    v_name = value["name"]
                    v_points = value["points"]
                    calculated_standings += f"{top_3_counter} - 🥈 {v_name} - {v_points} points\n"
                    top_3_counter += 1
                elif top_3_counter == 3:
                    v_name = value["name"]
                    v_points = value["points"]
                    calculated_standings += f"{top_3_counter} - 🥉 {v_name} - {v_points} points\n"
                    top_3_counter += 1
                elif top_3_counter >= 4 and top_3_counter <= 10:
                    v_name = value["name"]
                    v_points = value["points"]
                    calculated_standings += f"{top_3_counter} - 🏅 {v_name} - {v_points} points\n"
                    top_3_counter += 1
            
            while top_3_counter <= 10:
                calculated_standings += f"{top_3_counter} -\n"
                top_3_counter += 1
        
        embed_leaderboard = discord.Embed(title="**Art Fight Leaderboard**", description=calculated_standings, color=discord.Colour.light_embed())
        
        await interaction.response.send_message("", embed=embed_leaderboard, ephemeral=True)
    
async def setup(bot):
    await bot.add_cog(GeneralCog(bot))