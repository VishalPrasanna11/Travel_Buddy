import mobileimg from "../assets/mobile.png";
import hero from "../assets/hero.png";
// import SearchBar, { SearchForm } from "@/components/SearchBar";
import { useNavigate } from "react-router-dom";
const HomePage = () => {
  const navigate = useNavigate();
//   const handleSearchSubmit =(searchFormValues: SearchForm) => {
//     navigate({
//       pathname: `/search/${searchFormValues.searchQuery}`,
//     })
//   }
  return (
    <div className="flex flex-col gap-12">
        <div className="bg-white round-lg shadow-md py-8 flex flex-col gap-5 text-center -mt-16">
       <h1 className="text-5xl font-bold tracking-tight heroh1" style={{color:"#0A0A0A"}}> 
       Not all those who wander are lost 
       </h1>
       <span className="text-xl">Trip is just a click away!</span>
       {/* <SearchBar placeHolder="Search for City or Town"  onSubmit={handleSearchSubmit} /> */}
      </div>
      <div className="grid md:grid-cols-2 gap-5">
      {/* <img src={mobileimg}/> */}
      <div className="flex flex-col gap-5 items-center justify-center text-center">
        <span className="font-bold text-3xl tracking-tighter">
            Order from your favorite restaurants
        </span>
        <span>
            Download the app now!
        </span>
        <img src={hero}/>

    </div>
    </div>
    </div>
    
  );
}   
export default HomePage;