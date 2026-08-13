import { useState } from "react";


export default function AssetTable({
  assets,
  onSelect,
  selectedAssetId
}) {


  const [sortConfig, setSortConfig] = useState({
    key: "health_score",
    direction: "desc"
  });



  const handleSort = (key)=>{

    setSortConfig(prev=>({

      key,

      direction:
      prev.key === key &&
      prev.direction === "asc"
      ?
      "desc"
      :
      "asc"

    }));

  };



  const sortedAssets = [...(assets || [])].sort((a,b)=>{


    const valueA = a[sortConfig.key];
    const valueB = b[sortConfig.key];


    if(valueA < valueB)
      return sortConfig.direction==="asc"
      ? -1
      : 1;


    if(valueA > valueB)
      return sortConfig.direction==="asc"
      ? 1
      : -1;


    return 0;

  });



  const statusStyle=(status)=>{


    switch(status){

      case "Critical":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";


      case "Warning":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";


      case "Excellent":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";


      case "Good":
        return "bg-teal-500/10 text-teal-400 border-teal-500/30";


      default:
        return "bg-slate-500/10 text-slate-400";

    }

  };



  return (

    <div
    className="
    bg-paper-raised
    dark:bg-panel
    border
    border-slate-200
    dark:border-slate-800
    rounded-xl
    p-5
    "
    >


      <h3
      className="
      font-display
      text-sm
      font-medium
      text-ink
      dark:text-slate-200
      mb-4
      "
      >
        Fleet Assets
      </h3>



      <div className="overflow-x-auto">


      <table className="w-full text-sm">


        <thead>


          <tr
          className="
          text-left
          text-xs
          uppercase
          tracking-wider
          text-slate-500
          border-b
          border-slate-200
          dark:border-slate-800
          "
          >


            <th
            className="py-3 cursor-pointer"
            onClick={()=>handleSort("asset_id")}
            >
              Asset
            </th>


            <th
            className="cursor-pointer"
            onClick={()=>handleSort("asset_type")}
            >
              Type
            </th>


            <th
            className="cursor-pointer"
            onClick={()=>handleSort("health_score")}
            >
              Health
            </th>


            <th
            className="cursor-pointer"
            onClick={()=>handleSort("status")}
            >
              Status
            </th>


            <th
            className="cursor-pointer"
            onClick={()=>handleSort("predicted_rul_cycles")}
            >
              RUL Days
            </th>


          </tr>


        </thead>




        <tbody>


        {
          sortedAssets.map(asset=>(


          <tr

          key={asset.asset_id}

          onClick={()=>
            onSelect(asset.asset_id)
          }

          className={`
          border-b
          border-slate-200
          dark:border-slate-800
          cursor-pointer
          transition

          hover:bg-slate-100
          dark:hover:bg-slate-800/50

          ${
          selectedAssetId===asset.asset_id
          ?
          "bg-blue-500/10"
          :
          ""
          }

          `}

          >



            <td className="py-3 font-medium">

              {asset.name}

              <div
              className="
              text-xs
              text-slate-500
              font-mono
              "
              >
                {asset.asset_id}
              </div>

            </td>



            <td>

              {asset.asset_type}

            </td>




            <td className="w-48">


              <div className="flex items-center gap-3">


                <div
                className="
                flex-1
                h-2
                rounded-full
                bg-slate-200
                dark:bg-slate-700
                overflow-hidden
                "
                >

                  <div

                  className={`
                  h-full
                  rounded-full

                  ${
                  asset.health_score < 50
                  ?
                  "bg-rose-500"
                  :
                  asset.health_score < 80
                  ?
                  "bg-amber-400"
                  :
                  asset.health_score < 92
                  ?
                  "bg-teal-400"
                  :
                  "bg-emerald-400"
                  }

                  `}

                  style={{
                    width:`${asset.health_score}%`
                  }}

                  />

                </div>


                <span>
                  {asset.health_score}%
                </span>


              </div>


            </td>




            <td>


              <span
              className={`
              px-3
              py-1
              rounded-full
              border
              text-xs

              ${statusStyle(asset.status)}

              `}
              >

              {asset.status}

              </span>


            </td>





            <td>

              {asset.predicted_rul_cycles}

            </td>



          </tr>


          ))

        }


        </tbody>



      </table>


      </div>


    </div>


  );

}