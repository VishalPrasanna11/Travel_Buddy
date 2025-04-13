import type { MenuItem } from "../types";
import { Link } from "react-router-dom";
import { MessageSquare, Search, BookmarkIcon, Bell, Lightbulb, Plus } from "lucide-react";


const MenuItem = () => {
  return (
    <nav className="flex-1 p-4">
                <ul className="space-y-6">
                    <li>
                        <Link to="/chat" className="flex items-center text-gray-800 hover:text-black">
                            <MessageSquare className="mr-3 h-5 w-5" />
                            <span>Chats</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/explore" className="flex items-center text-gray-800 hover:text-black">
                            <Search className="mr-3 h-5 w-5" />
                            <span>Explore</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/saved" className="flex items-center text-gray-800 hover:text-black">
                            <BookmarkIcon className="mr-3 h-5 w-5" />
                            <span>Saved</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/updates" className="flex items-center text-gray-800 hover:text-black">
                            <Bell className="mr-3 h-5 w-5" />
                            <span>Updates</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/inspiration" className="flex items-center text-gray-800 hover:text-black">
                            <Lightbulb className="mr-3 h-5 w-5" />
                            <span>Inspiration</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/create" className="flex items-center text-gray-800 hover:text-black">
                            <Plus className="mr-3 h-5 w-5" />
                            <span>Create</span>
                        </Link>
                    </li>
                </ul>
            </nav>
  );
};

export default MenuItem;